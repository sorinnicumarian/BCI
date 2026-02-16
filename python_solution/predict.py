COLS = [
    'E_alpha', 'E_beta', 'E_theta', 'E_delta',
    'alpha_beta_ratio', 'theta_alpha_ratio', 'beta_theta_ratio', 'engagement_index',
    'beta_percentage',
    'peak_frequency', 'spectral_centroid', 'spectral_slope',
    'hjorth_mobility', 'hjorth_complexity', 'zero_crossing_rate', 'signal_variance',
    'smoothed_beta', 'smoothed_alpha', 'smoothed_ratio'
]
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Real-time EEG predictor (UNO R4 + BioAmp) using model.pkl + scaler.pkl

Fixes:
- Proper 50 Hz notch (Hz + Q=30, fs=512)
- Stable 0.5–30 Hz band-pass (SOS + sosfiltfilt)
- 1 s windows (512 samples) + artifact rejection BEFORE filtering
- Safe feature computation (peak in 0.5–30 Hz, slope in 2–30 Hz)
- Enforce column order before scaler.transform to avoid mis-mapping
- Robust serial port picker (prefer /dev/cu.usbmodem*, avoid debug console)
- Optional majority voting for flicker-free control
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
WIN = 512                # 1 s window @ 512 Hz (use 1024 for 2 s windows if you retrain)
Z_MAX = 5.0              # z-score gate (artifact rejection)
STD_MIN = 1e-3           # flat window guard
THRESH = 0.75            # decision threshold on predicted class prob (if you add proba)
VOTE_LEN = 5             # majority vote length (set to 1 to disable)

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
    try:
        while True:
            line = ser.readline()
            if not line:
                continue
            try:
                v = float(line.decode("utf-8", errors="ignore").strip())
            except ValueError:
                continue

            block.append(v)
            if len(block) < WIN:
                continue

            # Prepare 1 s window
            x = np.asarray(block, dtype=np.float32)

            # Artifact rejection BEFORE filtering
            std = x.std()
            if std < STD_MIN:
                block.clear()
                continue
            zmax = np.max(np.abs((x - x.mean()) / (std + 1e-9)))
            if zmax > Z_MAX:
                block.clear()
                continue

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


            # sanity: verify scaler expects 8 features
            assert hasattr(scaler, "mean_") and scaler.mean_.shape[0] == len(COLS), \
                f"Scaler expects {scaler.mean_.shape[0]} features, but live has {len(COLS)}"

            # Scale + predict with your saved scaler/model
            X_scaled = scaler.transform(df)          # DO NOT change column order!
            pred = int(clf.predict(X_scaled)[0])

            # Optional smoothing via majority vote (2-of-3)
            votes.append(pred)
            if VOTE_LEN > 1:
                pred = int(sum(votes) >= (VOTE_LEN // 2 + 1))

            # Print raw features that matter
            print("Live feats:",
                f"E_alpha={df.E_alpha.values[0]:.3f}",
                f"E_beta={df.E_beta.values[0]:.3f}",
                f"ratio={df.alpha_beta_ratio.values[0]:.3f}",
                f"pf={df.peak_frequency.values[0]:.2f}",
                f"slope={df.spectral_slope.values[0]:.2f}")

            X_scaled = scaler.transform(df)
            # Optional: look at scaled values once
            print("Scaled (first 4):", np.round(X_scaled[0,:4], 3))

            # Use probabilities + threshold
            if hasattr(clf, "predict_proba"):
                proba1 = float(clf.predict_proba(X_scaled)[0,1])
                print(f"p_focus={proba1:.3f}")
                pred = int(proba1 >= 0.50)  # tune later
            else:
                # fallback
                pred = int(clf.predict(X_scaled)[0])

            print(f"pred={pred}")

            # Optional keystroke (macOS: allow Accessibility)
            if HAVE_PYAUTOGUI:
                key = 'w' if pred == 1 else 'space'
                pyautogui.keyDown(key)
                time.sleep(0.2)
                pyautogui.keyUp(key)

            block.clear()  # non-overlapping 1 s windows; remove if you later want overlap
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