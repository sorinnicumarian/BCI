#!/Users/sorin/Documents/Repos/BCI/python_solution/.venv/bin/python
# -*- coding: utf-8 -*-
"""
Real-time 4-Class EEG+EOG Mouse Control (UNO R4 + BioAmp)
Dataset 06: RelaxUp / FocusDown / CountBackRight / SingLeft

Two parallel pipelines:
  1. Per-sample IIR (Notch → LPF → HPF) → EOG envelope → blink/click detection
  2. Rolling 512-sample window (scipy filtfilt) → 19 features → SVM → mouse direction

Class → action:
  0  RelaxUp        → mouse UP
  1  FocusDown      → mouse DOWN
  2  CBRight        → mouse RIGHT
  3  SingLeft       → mouse LEFT
  double blink      → left click
"""

import os
import pickle
import time
import warnings
from collections import deque

import numpy as np
import pandas as pd
import serial
import serial.tools.list_ports as list_ports
from scipy import signal as scipy_signal

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    HAVE_PYAUTOGUI = True
except Exception:
    HAVE_PYAUTOGUI = False

warnings.filterwarnings("ignore")

# ================== CONFIG ==================
FS       = 512
WIN      = 512          # 1 s window for ML
STEP     = 256          # 50% overlap → prediction every 0.5 s
VOTE_LEN = 3            # majority vote over last N predictions
STD_MIN  = 1e-3         # flat-signal guard (catches dead/disconnected electrode)
# Artifact rejection: fraction-based (robust to single blinks/saccades)
# Rejects window only if >50% of samples are extreme outliers (z > 4)
# A blink affects ~20% of a 1s window → passes. Floating electrode → fails.
ARTIFACT_Z      = 4.0   # per-sample z threshold for outlier detection
ARTIFACT_FRAC   = 0.50  # fraction of outlier samples to reject window

# ---- Hybrid cascade thresholds ----
# RelaxUp  : beta_pct < BETA_RELAX_THRESH   (notebook mean: 10.4%, next class: 13.9%)
# FocusDown: E_alpha  > ALPHA_FOCUS_THRESH  (notebook mean: 0.159, next class: 0.112)
# CBRight / SingLeft: ML (argmax of class 2 vs 3 probabilities)
BETA_RELAX_THRESH  = 13.0   # below → RelaxUp
ALPHA_FOCUS_THRESH = 0.13   # above (and beta > BETA_RELAX_THRESH) → FocusDown

# EOG blink detection (per-sample IIR pipeline)
BLINK_LOWER        = 30.0
BLINK_UPPER        = 50.0
BLINK_DEBOUNCE_MS  = 200
DOUBLE_BLINK_MS    = 500
ENVELOPE_WINDOW    = int(0.1 * FS)   # 51 samples

# Mouse
MOUSE_SPEED    = 8      # pixels per move event
MOVE_EVERY_MS  = 50     # fire movement every 50 ms

SMOOTHING_FACTOR = 0.63
EPS = 1e-12

# Feature column order — must match notebook training exactly
COLS = [
    'E_alpha', 'E_beta', 'E_theta', 'E_delta',
    'alpha_beta_ratio', 'theta_alpha_ratio', 'beta_theta_ratio', 'engagement_index',
    'beta_percentage',
    'peak_frequency', 'spectral_centroid', 'spectral_slope',
    'hjorth_mobility', 'hjorth_complexity', 'zero_crossing_rate', 'signal_variance',
    'smoothed_beta', 'smoothed_alpha', 'smoothed_ratio',
    'signal_skewness', 'signal_kurtosis', 'peak_to_peak', 'line_length',
    'window_mean', 'window_mean_abs',
]

CLASS_NAMES = {0: 'RelaxUp', 1: 'FocusDown', 2: 'CBRight', 3: 'SingLeft'}
MOUSE_MOVE  = {0: (0, -MOUSE_SPEED), 1: (0, MOUSE_SPEED),
               2: (MOUSE_SPEED, 0), 3: (-MOUSE_SPEED, 0)}


# ================== PER-SAMPLE IIR (EOG pipeline) ==================
class Biquad:
    __slots__ = ("sa1", "a2", "b0", "b1", "b2", "z1", "z2")
    def __init__(self, sa1, a2, b0, b1, b2):
        self.sa1=sa1; self.a2=a2; self.b0=b0; self.b1=b1; self.b2=b2
        self.z1=0.0;  self.z2=0.0
    def process(self, inp):
        w=inp-self.sa1*self.z1-self.a2*self.z2
        out=self.b0*w+self.b1*self.z1+self.b2*self.z2
        self.z2=self.z1; self.z1=w
        return out

def make_iir_filters():
    notch1  = Biquad(-1.58696045, 0.96505858,  0.96588529, -1.57986211,  0.96588529)
    notch2  = Biquad(-1.62761184, 0.96671306,  1.00000000, -1.63566226,  1.00000000)
    eeg_lpf = Biquad(-1.24200128, 0.45885207,  0.05421270,  0.10842539,  0.05421270)
    eog_hpf = Biquad(-1.91327599, 0.91688335,  0.95753983, -1.91507967,  0.95753983)
    return notch1, notch2, eeg_lpf, eog_hpf


# ================== SCIPY FILTERS (ML window pipeline) ==================
def make_scipy_filters():
    b_notch, a_notch = scipy_signal.iirnotch(w0=50.0, Q=30.0, fs=FS)
    sos_bp = scipy_signal.butter(4, [0.5, 30.0], btype='band', fs=FS, output='sos')
    return b_notch, a_notch, sos_bp

def filter_window(x, b_notch, a_notch, sos_bp):
    x_notched = scipy_signal.filtfilt(b_notch, a_notch, x)    # notch only (preserves DC)
    x_bp      = scipy_signal.sosfiltfilt(sos_bp, x_notched)   # + bandpass
    return x_bp, x_notched


# ================== FEATURE EXTRACTION (matches notebook) ==================
def extract_features(x, sm_alpha, sm_beta, x_notched=None):
    f, psd = scipy_signal.welch(x, fs=FS, nperseg=len(x))

    # Band energies (relative to 0.5–30 Hz)
    total = psd[(f >= 0.5) & (f <= 30.0)].sum() + EPS
    E_alpha = psd[(f >= 8)  & (f <= 13)].sum() / total
    E_beta  = psd[(f >= 13) & (f <= 30)].sum() / total
    E_theta = psd[(f >= 4)  & (f <= 7)].sum()  / total
    E_delta = psd[(f >= 0.5)& (f <= 3)].sum()  / total

    alpha_beta_ratio  = (E_alpha + EPS) / (E_beta  + EPS)
    theta_alpha_ratio = (E_theta + EPS) / (E_alpha + EPS)
    beta_theta_ratio  = (E_beta  + EPS) / (E_theta + EPS)
    engagement_index  = E_beta / (E_alpha + E_theta + EPS)
    beta_percentage   = E_beta * 100.0

    # Spectral features
    idx_pb    = (f >= 0.5) & (f <= 30.0)
    idx_slope = (f >= 2.0) & (f <= 30.0)
    peak_frequency   = float(f[idx_pb][np.argmax(psd[idx_pb])])
    spectral_centroid= float((f[idx_pb] * psd[idx_pb]).sum() / (psd[idx_pb].sum() + EPS))
    logf = np.log10(f[idx_slope] + EPS)
    logp = np.log10(psd[idx_slope] + EPS)
    spectral_slope   = float(np.polyfit(logf, logp, 1)[0])

    # Temporal features
    dx  = np.diff(x)
    dx2 = np.diff(dx)
    hjorth_mobility   = np.std(dx)  / (np.std(x)  + EPS)
    hjorth_complexity = (np.std(dx2) / (np.std(dx) + EPS)) / (hjorth_mobility + EPS)
    zero_crossing_rate= float(np.sum(np.diff(np.sign(x)) != 0) / len(x))
    signal_variance   = float(np.var(x))

    # NEW: amplitude statistics (skewness, kurtosis, peak-to-peak, line length)
    mu, sigma = x.mean(), x.std() + EPS
    signal_skewness = float(np.mean(((x - mu) / sigma) ** 3))
    signal_kurtosis = float(np.mean(((x - mu) / sigma) ** 4) - 3.0)
    peak_to_peak    = float(x.max() - x.min())
    line_length     = float(np.sum(np.abs(dx)))

    # Exponential smoothing (same as notebook)
    sm_beta_new  = SMOOTHING_FACTOR * E_beta  + (1 - SMOOTHING_FACTOR) * sm_beta
    sm_alpha_new = SMOOTHING_FACTOR * E_alpha + (1 - SMOOTHING_FACTOR) * sm_alpha
    sm_ratio     = (sm_alpha_new + EPS) / (sm_beta_new + EPS)

    feat = {
        'E_alpha': E_alpha, 'E_beta': E_beta, 'E_theta': E_theta, 'E_delta': E_delta,
        'alpha_beta_ratio': alpha_beta_ratio, 'theta_alpha_ratio': theta_alpha_ratio,
        'beta_theta_ratio': beta_theta_ratio, 'engagement_index': engagement_index,
        'beta_percentage': beta_percentage,
        'peak_frequency': peak_frequency, 'spectral_centroid': spectral_centroid,
        'spectral_slope': spectral_slope,
        'hjorth_mobility': hjorth_mobility, 'hjorth_complexity': hjorth_complexity,
        'zero_crossing_rate': zero_crossing_rate, 'signal_variance': signal_variance,
        'smoothed_beta': sm_beta_new, 'smoothed_alpha': sm_alpha_new,
        'smoothed_ratio': sm_ratio,
        'signal_skewness': signal_skewness, 'signal_kurtosis': signal_kurtosis,
        'peak_to_peak': peak_to_peak, 'line_length': line_length,
        # DC eye position: from notch-only signal (before HPF destroys sustained gaze shift)
        'window_mean':     float(np.mean(x_notched)) if x_notched is not None else 0.0,
        'window_mean_abs': float(np.abs(np.mean(x_notched))) if x_notched is not None else 0.0,
    }
    return feat, sm_alpha_new, sm_beta_new


# ================== SERIAL PORT ==================
def pick_port():
    env = os.environ.get("BCI_PORT")
    if env:
        return env
    ports = list(list_ports.comports())
    if not ports:
        raise RuntimeError("No serial ports found.")
    for p in ports:
        if "usbmodem" in p.device.lower():
            return p.device
    for p in ports:
        if p.device.lower().startswith("/dev/cu.usb") and "debug" not in p.device.lower():
            return p.device
    EXCLUDE = ("debug", "bluetooth", "bt-")
    for p in ports:
        if not any(x in p.device.lower() for x in EXCLUDE):
            return p.device
    raise RuntimeError("No suitable port found (only debug/Bluetooth detected). "
                       "Set BCI_PORT env var to override.")


# ================== LOAD MODEL ==================
def load_model():
    base = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base, "model.pkl"),  "rb") as f: clf    = pickle.load(f)
    with open(os.path.join(base, "scaler.pkl"), "rb") as f: scaler = pickle.load(f)
    return clf, scaler


# ================== MAIN ==================
def main():
    port = pick_port()
    print(f"[INFO] Opening {port} @ 115200")
    ser = serial.Serial(port, 115200, timeout=1)

    clf, scaler = load_model()
    b_notch, a_notch, sos_bp = make_scipy_filters()
    notch1, notch2, eeg_lpf, eog_hpf = make_iir_filters()

    # Rolling raw buffer for ML windowing
    raw_buf  = deque(maxlen=WIN)
    step_ctr = 0

    # Exponential smoothing state
    sm_alpha = 0.0
    sm_beta  = 0.0

    # Majority vote buffer
    votes = deque(maxlen=VOTE_LEN)

    # EOG envelope (per-sample)
    env_buf = np.zeros(ENVELOPE_WINDOW, dtype=np.float64)
    env_sum = 0.0
    env_idx = 0
    eog_env = 0.0

    # Blink state machine
    blink_count    = 0
    first_blink_ms = 0.0
    last_blink_ms  = 0.0

    # Current predicted class and mouse timing
    current_class  = -1   # -1 = no prediction yet
    last_move_ms   = time.monotonic() * 1000.0
    last_print_ms  = 0.0

    # Latest feature snapshot for per-second printing
    last_feat      = None
    last_method    = ""
    last_voted     = -1
    last_votes_str = ""
    last_valid_win_ms = 0.0   # timestamp of last accepted ML window

    print("[INFO] Streaming... (Ctrl+C to stop)")
    print("[INFO] Classes: 0=RelaxUp ↑  1=FocusDown ↓  2=CBRight →  3=SingLeft ←")
    print("[INFO] Double blink → left click")
    print()
    print("  β%  = beta band power %       (low β → RelaxUp linear rule)")
    print("  α%  = alpha band power %      (high α → FocusDown linear rule)")
    print("  δ%  = delta band power %      (movement/noise indicator, ideally low)")
    print("  θ%  = theta band power %")
    print("  w_mean = raw DC level        (eye position: ~480 left, ~520 right)")
    print("  pCB = ML prob → CBRight      (only shown when linear rules don't fire)")
    print("  pSL = ML prob → SingLeft     (only shown when linear rules don't fire)")
    print("  method = what made the decision: linear rule or ML")
    print("  votes  = last 3 predictions  (majority wins)")
    print()

    try:
        while True:
            line = ser.readline()
            if not line:
                continue
            try:
                raw = float(line.decode("utf-8", errors="ignore").strip())
            except ValueError:
                continue

            # ---- Per-sample IIR chain (EOG blink detection) ----
            s       = notch1.process(raw)
            s       = notch2.process(s)
            eeg_s   = eeg_lpf.process(s)
            eog_s   = eog_hpf.process(eeg_s)

            abs_eog          = abs(eog_s)
            env_sum         -= env_buf[env_idx]
            env_sum         += abs_eog
            env_buf[env_idx] = abs_eog
            env_idx          = (env_idx + 1) % ENVELOPE_WINDOW
            eog_env          = env_sum / ENVELOPE_WINDOW

            # ---- Blink state machine ----
            now_ms = time.monotonic() * 1000.0
            if BLINK_LOWER < eog_env < BLINK_UPPER and (now_ms - last_blink_ms) >= BLINK_DEBOUNCE_MS:
                last_blink_ms = now_ms
                if blink_count == 0:
                    first_blink_ms = now_ms
                    blink_count = 1
                elif blink_count == 1 and (now_ms - first_blink_ms) <= DOUBLE_BLINK_MS:
                    blink_count = 2
                else:
                    first_blink_ms = now_ms
                    blink_count = 1

            if blink_count == 2 and (now_ms - first_blink_ms) > DOUBLE_BLINK_MS:
                print("[BLINK] Double blink → LEFT CLICK")
                if HAVE_PYAUTOGUI:
                    pyautogui.click()
                blink_count = 0

            if blink_count == 1 and (now_ms - first_blink_ms) > DOUBLE_BLINK_MS:
                blink_count = 0

            # ---- ML windowing ----
            raw_buf.append(raw)
            step_ctr += 1

            if len(raw_buf) >= WIN and step_ctr >= STEP:
                step_ctr = 0
                x = np.asarray(raw_buf, dtype=np.float64)

                # Artifact rejection
                std = x.std()
                if std < STD_MIN:                          # flat/dead electrode
                    continue
                if x.max() > 1000 or x.min() < 20:        # ADC saturation (near rail)
                    continue
                z = np.abs((x - x.mean()) / (std + 1e-9))
                if np.mean(z > ARTIFACT_Z) > ARTIFACT_FRAC:  # >50% samples extreme → persistent noise
                    continue

                # Filter + features
                xf, xf_notched = filter_window(x, b_notch, a_notch, sos_bp)
                feat, sm_alpha, sm_beta = extract_features(xf, sm_alpha, sm_beta, xf_notched)

                # ---- Hybrid cascade ----
                beta_pct = feat['beta_percentage']
                E_alpha  = feat['E_alpha']

                pCB = pSL = float('nan')
                if beta_pct < BETA_RELAX_THRESH:
                    pred   = 0
                    method = f"linear β<{BETA_RELAX_THRESH}"
                elif E_alpha > ALPHA_FOCUS_THRESH:
                    pred   = 1
                    method = f"linear α>{ALPHA_FOCUS_THRESH}"
                else:
                    df_feat  = pd.DataFrame([feat])[COLS]
                    X_scaled = scaler.transform(df_feat)
                    proba    = clf.predict_proba(X_scaled)[0]
                    pCB, pSL = proba[0], proba[1]
                    pred     = 2 if pCB >= pSL else 3
                    method   = f"ML"

                votes.append(pred)
                voted     = int(max(set(votes), key=list(votes).count))
                vote_str  = ''.join(str(v) for v in votes)

                if voted != current_class:
                    current_class = voted

                # Store latest snapshot for per-second print
                last_feat      = feat
                last_method    = method
                last_voted     = voted
                last_votes_str = vote_str
                last_pCB, last_pSL = pCB, pSL
                last_valid_win_ms  = now_ms

            # ---- Print row every second ----
            if (now_ms - last_print_ms) >= 1000.0:
                last_print_ms = now_ms
                stale_s = (now_ms - last_valid_win_ms) / 1000.0
                if last_valid_win_ms == 0.0:
                    raw_now = raw_buf[-1] if raw_buf else 0
                    print(f"⏳ Waiting for first valid window...  raw={raw_now:.0f}")
                elif stale_s > 5.0:
                    raw_now = raw_buf[-1] if raw_buf else 0
                    print(f"⚠  SIGNAL LOST ({stale_s:.0f}s) — check electrode  raw={raw_now:.0f}")
                else:
                    f = last_feat
                    pcb_str = f"pCB={last_pCB:.2f}" if not np.isnan(last_pCB) else ""
                    psl_str = f"pSL={last_pSL:.2f}" if not np.isnan(last_pSL) else ""
                    ml_str  = f"  {pcb_str} {psl_str}" if pcb_str else ""
                    print(f"β={f['beta_percentage']:.1f}%  α={f['E_alpha']*100:.1f}%  "
                          f"δ={f['E_delta']*100:.1f}%  θ={f['E_theta']*100:.1f}%  "
                          f"w_mean={f['window_mean']:.1f}  "
                          f"| method={last_method}{ml_str}  "
                          f"| votes=[{last_votes_str}] → {CLASS_NAMES[last_voted]}")

            # ---- Mouse movement every MOVE_EVERY_MS ----
            if now_ms - last_move_ms >= MOVE_EVERY_MS:
                last_move_ms = now_ms
                if HAVE_PYAUTOGUI and current_class in MOUSE_MOVE:
                    dx, dy = MOUSE_MOVE[current_class]
                    pyautogui.move(dx, dy, duration=0)

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
