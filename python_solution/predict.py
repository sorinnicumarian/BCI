#!/Users/sorin/Documents/Repos/BCI/python_solution/.venv/bin/python
# -*- coding: utf-8 -*-
"""
Real-time EEG 3-Class Mouse Control (UNO R4 + BioAmp)

Classes (Best 3 from 5-class evaluation):
0 = Relax/Down (move cursor DOWN)
1 = Focus/Up (move cursor UP)
2 = Jaw Clench (move cursor LEFT) - Perry-inspired with EMG

Features:
- 3-class SVM classification (dropped Left Fist 49.2%, Count Backwards 53.8%)
- Fast predictions (4 Hz, STEP=128)
- Confidence threshold (0.50) for REST state
- UP boost (1.3x) for better detection
- Expected accuracy: 65-75%
"""

import os
import time
import warnings
from collections import deque

import numpy as np
import pandas as pd
import serial
import serial.tools.list_ports as list_ports
from scipy import signal
import pickle

# Optional: keyboard control (grant Accessibility on macOS)
try:
    import pyautogui
    HAVE_PYAUTOGUI = True
except Exception:
    HAVE_PYAUTOGUI = False

warnings.filterwarnings("ignore", category=UserWarning)

# -----------------------------
# CONFIG
# -----------------------------
FS = 512                 # sampling rate (Hz)
WIN = 512                # 1 s window @ 512 Hz
STEP = 128               # step size: 128 = 0.25s (4 pred/s FAST), 256 = 0.5s, 512 = 1s
Z_MAX = 6.0              # z-score gate (artifact rejection) - matches training notebook
STD_MIN = 1e-3           # flat window guard
VOTE_LEN = 1             # majority vote disabled - raw predictions for fast response

# Mouse Control Settings (3-class)
MOUSE_SPEED = 15         # pixels per prediction for left movement
MOUSE_UP_SPEED = 10      # pixels per prediction for up/down movement
CONFIDENCE_THRESHOLD = 0.50  # min confidence to move cursor (below = REST/stay)

# Per-class probability boost factors [DOWN, UP, JAW]
CLASS_BOOST_FACTORS = [1.0, 1.6, 0.54]  
# DOWN=1.0 (no change), UP=1.5 (50% boost), JAW=0.8 (20% reduction)

# IMPORTANT: must match training feature order exactly
COLS = [
    'E_alpha', 'E_beta', 'E_theta', 'E_delta',
    'alpha_beta_ratio', 'theta_alpha_ratio', 'beta_theta_ratio', 'engagement_index',
    'beta_percentage',
    'peak_frequency', 'spectral_centroid', 'spectral_slope',
    'hjorth_mobility', 'hjorth_complexity', 'zero_crossing_rate', 'signal_variance',
    'smoothed_beta', 'smoothed_alpha', 'smoothed_ratio'
]

# If your current model.pkl/scaler.pkl were trained on *absolute* bandpowers,
# keep the feature function below as relative or switch to absolute consistently in training too.
# For now we keep relative powers because this is the robust setting going forward.
# If you did NOT retrain yet, and your model needs absolute powers, ping me and I’ll give the absolute version.


# -----------------------------
# Serial port selection
# -----------------------------
def pick_port():
    """
    Prefer UNO R4 native CDC (/dev/cu.usbmodem*) on macOS.
    Avoid debug-console. Allow override via BCI_PORT env var.
    """
    env = os.environ.get("BCI_PORT")
    if env:
        return env

    ports = list(list_ports.comports())
    if not ports:
        raise RuntimeError("No serial ports found. Plug the board and try again.")

    # 1) Prefer usbmodem
    for p in ports:
        if "usbmodem" in p.device.lower():
            return p.device

    # 2) Any cu.usb* except debug
    for p in ports:
        dev = p.device.lower()
        if dev.startswith("/dev/cu.usb") and "debug" not in dev:
            return p.device

    # 3) Last resort: first non-debug
    for p in ports:
        if "debug" not in p.device.lower():
            return p.device

    return ports[0].device


# -----------------------------
# Filters (correct & stable)
# -----------------------------
def setup_filters(fs: int):
    """
    Proper 50 Hz notch (Hz + Q=30) and stable 0.5–30 Hz band-pass (SOS).
    """
    b_notch, a_notch = signal.iirnotch(w0=50.0, Q=30.0, fs=fs)                     # Step 1 (correct units + Q)
    sos_bp = signal.butter(4, [0.5, 30.0], btype='band', fs=fs, output='sos')      # Step 2 (SOS)
    return b_notch, a_notch, sos_bp


def process_block(x: np.ndarray, b_notch, a_notch, sos_bp):
    """
    Zero-phase notch, then SOS band-pass for a single block.
    """
    x = signal.filtfilt(b_notch, a_notch, x)
    x = signal.sosfiltfilt(sos_bp, x)
    return x


# -----------------------------
# Feature extraction (robust)
# -----------------------------
def calculate_psd_features(x: np.ndarray, fs: int):
    """
    Relative bandpowers + frequency ratios (robust across sessions).
    """
    f, psd = signal.welch(x, fs=fs, nperseg=len(x))
    total = psd[(f >= 0.5) & (f <= 30.0)].sum() + 1e-12

    E_alpha = psd[(f >= 8)  & (f <= 13)].sum() / total
    E_beta  = psd[(f >= 13) & (f <= 30)].sum() / total
    E_theta = psd[(f >= 4)  & (f <= 7)].sum()  / total
    E_delta = psd[(f >= 0.5)& (f <= 3)].sum()  / total

    alpha_beta_ratio = (E_alpha + 1e-12) / (E_beta + 1e-12)
    theta_alpha_ratio = (E_theta + 1e-12) / (E_alpha + 1e-12)
    beta_theta_ratio = (E_beta + 1e-12) / (E_theta + 1e-12)
    engagement_index = E_beta / (E_alpha + E_theta + 1e-12)

    # Arduino-inspired: beta as percentage
    beta_percentage = E_beta * 100.0

    return {
        'E_alpha': E_alpha, 'E_beta': E_beta,
        'E_theta': E_theta, 'E_delta': E_delta,
        'alpha_beta_ratio': alpha_beta_ratio,
        'theta_alpha_ratio': theta_alpha_ratio,
        'beta_theta_ratio': beta_theta_ratio,
        'engagement_index': engagement_index,
        'beta_percentage': beta_percentage
    }


def calculate_additional_features(x: np.ndarray, fs: int):
    """
    Peak in 0.5–30 Hz (avoid DC), slope in 2–30 Hz (log10), centroid in passband.
    """
    f, psd = signal.welch(x, fs=fs, nperseg=len(x))

    idx_pb = (f >= 0.5) & (f <= 30.0)
    peak_frequency = float(f[idx_pb][np.argmax(psd[idx_pb])])

    idx_slope = (f >= 2.0) & (f <= 30.0)
    logf = np.log10(f[idx_slope] + 1e-12)
    logp = np.log10(psd[idx_slope] + 1e-12)
    spectral_slope = float(np.polyfit(logf, logp, 1)[0])

    spectral_centroid = float((f[idx_pb] * psd[idx_pb]).sum() / (psd[idx_pb].sum() + 1e-12))

    return {
        'peak_frequency': peak_frequency,
        'spectral_centroid': spectral_centroid,
        'spectral_slope': spectral_slope
    }


def calculate_temporal_features(x: np.ndarray):
    """
    Time-domain features capturing signal dynamics
    """
    # Hjorth mobility (mean frequency indicator)
    diff_x = np.diff(x)
    hjorth_mobility = np.std(diff_x) / (np.std(x) + 1e-12)

    # Hjorth complexity (change in frequency)
    diff2_x = np.diff(diff_x)
    mobility2 = np.std(diff2_x) / (np.std(diff_x) + 1e-12)
    hjorth_complexity = mobility2 / (hjorth_mobility + 1e-12)

    # Zero-crossing rate (rough frequency estimate)
    zero_crossings = np.sum(np.diff(np.sign(x)) != 0) / len(x)

    # Signal variance (overall power)
    variance = np.var(x)

    return {
        'hjorth_mobility': hjorth_mobility,
        'hjorth_complexity': hjorth_complexity,
        'zero_crossing_rate': zero_crossings,
        'signal_variance': variance
    }


def extract_features(x: np.ndarray, fs: int):
    feats = calculate_psd_features(x, fs)
    feats.update(calculate_additional_features(x, fs))
    feats.update(calculate_temporal_features(x))
    return feats


# -----------------------------
# Load model + scaler (no Pipeline)
# -----------------------------
def load_model_and_scaler():
    base = os.path.dirname(os.path.abspath(__file__))
    model_path  = os.path.join(base, "model.pkl")
    scaler_path = os.path.join(base, "scaler.pkl")

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"model.pkl not found at: {model_path}")
    if not os.path.exists(scaler_path):
        raise FileNotFoundError(f"scaler.pkl not found at: {scaler_path}")

    with open(model_path,  "rb") as f:
        clf = pickle.load(f)
    with open(scaler_path, "rb") as f:
        scaler = pickle.load(f)
    return clf, scaler


# -----------------------------
# Main loop
# -----------------------------
def main():
    # Serial port
    port = pick_port()
    print(f"[INFO] Opening {port} @ 115200")
    ser = serial.Serial(port, 115200, timeout=1)

    # Filters
    b_notch, a_notch, sos_bp = setup_filters(FS)

    # ML
    clf, scaler = load_model_and_scaler()

    # Buffers
    block = deque(maxlen=WIN)
    votes = deque(maxlen=VOTE_LEN)

    # Exponential smoothing state (Arduino-inspired)
    SMOOTHING_FACTOR = 0.63
    smoothed_alpha = 0.0
    smoothed_beta = 0.0

    print("[INFO] Streaming... (Ctrl+C to stop)")
    print("[INFO] 3-Class Mouse Control: DOWN↓ / UP↑ / JAW←")
    sample_count = 0
    try:
        while True:
            line = ser.readline()
            if not line:
                continue
            try:
                v = float(line.decode("utf-8", errors="ignore").strip())
            except ValueError:
                continue

            sample_count += 1
            # Debug: print every 512th sample (less spam with faster predictions)
            if sample_count % 512 == 0:
                print(f"[DEBUG] Received {sample_count} samples, latest: {v:.1f}, buffer: {len(block)}/512")

            block.append(v)
            if len(block) < WIN:
                continue

            # Prepare 1 s window
            x = np.asarray(block, dtype=np.float32)

            # Artifact rejection BEFORE filtering
            std = x.std()
            if std < STD_MIN:
                print(f"[DEBUG] Rejected: std too low ({std:.6f})")
                block.clear()
                continue
            zmax = np.max(np.abs((x - x.mean()) / (std + 1e-9)))
            if zmax > Z_MAX:
                print(f"[DEBUG] Rejected: z-score too high ({zmax:.2f})")
                block.clear()
                continue

            # print(f"[DEBUG] Processing window: std={std:.2f}, zmax={zmax:.2f}")  # Commented: too spammy at 2 Hz

            # Filters
            x = process_block(x, b_notch, a_notch, sos_bp)

            # Features
            feats = extract_features(x, FS)

            # Apply exponential smoothing (Arduino-inspired)
            smoothed_alpha = SMOOTHING_FACTOR * feats['E_alpha'] + (1 - SMOOTHING_FACTOR) * smoothed_alpha
            smoothed_beta = SMOOTHING_FACTOR * feats['E_beta'] + (1 - SMOOTHING_FACTOR) * smoothed_beta
            smoothed_ratio = (smoothed_alpha + 1e-12) / (smoothed_beta + 1e-12)

            # Add smoothed features to the feature dictionary
            feats['smoothed_alpha'] = smoothed_alpha
            feats['smoothed_beta'] = smoothed_beta
            feats['smoothed_ratio'] = smoothed_ratio

            # Enforce training column order EXACTLY
            df = pd.DataFrame([feats])[COLS]

            # Sanity: verify scaler expects correct number of features
            assert hasattr(scaler, "mean_") and scaler.mean_.shape[0] == len(COLS), \
                f"Scaler expects {scaler.mean_.shape[0]} features, but live has {len(COLS)}"

            # Scale features
            X_scaled = scaler.transform(df)

            # 4-class prediction
            pred = int(clf.predict(X_scaled)[0])

            # Get probabilities for diagnostics
            if hasattr(clf, "predict_proba"):
                probas = clf.predict_proba(X_scaled)[0]

                # Apply per-class boost factors [DOWN=1.0, UP=1.5, JAW=0.8]
                boosted_probas = probas.copy()
                for i in range(len(boosted_probas)):
                    boosted_probas[i] *= CLASS_BOOST_FACTORS[i]
                # Renormalize so probabilities sum to 1.0
                boosted_probas /= boosted_probas.sum()

                # Re-predict based on boosted probabilities
                pred = int(np.argmax(boosted_probas))

                # Check confidence threshold for REST state
                max_confidence = boosted_probas[pred]
            else:
                probas = None
                max_confidence = 1.0  # no confidence info, assume confident

            # Optional smoothing via majority vote
            votes.append(pred)
            if VOTE_LEN > 1:
                # For multi-class, use most common value
                pred = max(set(votes), key=votes.count)

            # Print diagnostics
            class_names = ['DOWN', 'UP', 'JAW']
            if probas is not None:
                # Show boosted probabilities (what the system actually uses)
                proba_str = " ".join([f"{class_names[i]}:{boosted_probas[i]:.2f}" for i in range(len(boosted_probas))])
                print(f"{proba_str} | pred={class_names[pred]} (conf={max_confidence:.2f})")
            else:
                print(f"pred={class_names[pred]}")

            # 3-class mouse control with confidence threshold
            if HAVE_PYAUTOGUI:
                if max_confidence < CONFIDENCE_THRESHOLD:
                    # Low confidence - REST (don't move cursor)
                    print("[MOUSE] ⏸ REST (low confidence)")
                elif pred == 0:
                    # DOWN/RELAX - move cursor DOWN
                    pyautogui.move(0, MOUSE_UP_SPEED, duration=0)
                    print("[MOUSE] ↓ DOWN")
                elif pred == 1:
                    # UP/FOCUS - move cursor UP
                    pyautogui.move(0, -MOUSE_UP_SPEED, duration=0)
                    print("[MOUSE] ↑ UP")
                elif pred == 2:
                    # JAW CLENCH - move cursor LEFT (Perry-inspired EMG signal)
                    pyautogui.move(-MOUSE_SPEED, 0, duration=0)
                    print("[MOUSE] ← JAW CLENCH")

            # Sliding window: remove STEP samples for overlap
            # STEP=256 → prediction every 0.5s, STEP=512 → every 1s
            for _ in range(min(STEP, len(block))):
                block.popleft()
    except KeyboardInterrupt:
        print("\n[INFO] Stopped by user.")
    finally:
        try:
            ser.close()
            print("[INFO] Serial closed.")
        except Exception:
            pass


if __name__ == "__main__":
    main()