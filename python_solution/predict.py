#!/Users/sorin/Documents/Repos/BCI/python_solution/.venv/bin/python
# -*- coding: utf-8 -*-
"""
Real-time 2-Class BCI — Linear rules only, no ML, no scipy.
Serial reading runs in its own thread; mouse runs in another.
Prints band powers every second regardless of signal state.

Class → mouse:
  0  Relax  (β low)   → UP
  1  Focus  (β high)  → DOWN
"""

import os
import time
import threading
import warnings
from collections import deque

import numpy as np
import serial
import serial.tools.list_ports as list_ports

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    HAVE_PYAUTOGUI = True
except Exception:
    HAVE_PYAUTOGUI = False

warnings.filterwarnings("ignore")

# ── CONFIG ────────────────────────────────────────────────────────────────────
FS   = 512
WIN  = 512   # 1 s window
STEP = 128   # slide 128 samples → 4 predictions/s

BETA_THRESH   = 13.0   # β% below → Relax ↑,  at or above → Focus ↓

# Optional 4-class model (default off). Train it with:
#   uv run scripts/judge.py --save python_solution/model4.pkl
# then run: BCI_MODEL=model4.pkl ./predict.py
BCI_MODEL = os.environ.get("BCI_MODEL", "")

MOUSE_STEP    = 8
MOVE_EVERY_MS = 50
EPS = 1e-12

CLASS_NAMES = {0: 'Relax ↑', 1: 'Focus ↓', 2: 'CB →', 3: 'Sing ←'}
MOUSE_MOVE  = {0: (0, -MOUSE_STEP), 1: (0, MOUSE_STEP),
               2: (MOUSE_STEP, 0), 3: (-MOUSE_STEP, 0)}


# ── SERIAL PORT ───────────────────────────────────────────────────────────────
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
    raise RuntimeError("No suitable port. Set BCI_PORT env var.")


# ── BAND POWERS (pure numpy, no scipy) ───────────────────────────────────────
def band_powers(x):
    # Remove linear trend (slow drift from movement/electrode) before FFT
    t  = np.arange(len(x))
    x  = x - np.polyval(np.polyfit(t, x, 1), t)
    xw    = x * np.hanning(len(x))
    psd   = np.abs(np.fft.rfft(xw)) ** 2
    freqs = np.fft.rfftfreq(len(x), 1.0 / FS)
    total = psd[(freqs >= 4.0) & (freqs <= 30.0)].sum() + EPS  # exclude delta from total
    E_d = psd[(freqs >= 0.5) & (freqs <= 4.0)].sum() / (total + EPS)
    E_t = psd[(freqs >= 4.0) & (freqs <= 8.0)].sum() / total
    E_a = psd[(freqs >= 8.0) & (freqs <= 13.0)].sum() / total
    E_b = psd[(freqs >= 13.0) & (freqs <= 30.0)].sum() / total
    return E_d * 100, E_t * 100, E_a * 100, E_b * 100


# ── FEATURES (shared with scripts/judge.py) ──────────────────────────────────
def features(x):
    d, t, a, b = band_powers(x)
    dx  = np.diff(x)
    var = x.var() + EPS
    mob  = np.sqrt(dx.var() / var)
    comp = np.sqrt(np.diff(dx).var() / (dx.var() + EPS)) / (mob + EPS)
    return [d, t, a, b, a / (b + EPS), b / (t + EPS),
            np.log(var), np.abs(dx).sum(), np.ptp(x), x.mean(), mob, comp]


def load_model(path):
    import pickle
    if not os.path.isabs(path):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
    with open(path, "rb") as f:
        return pickle.load(f)


# ── SERIAL READER THREAD ──────────────────────────────────────────────────────
# Runs in background; puts raw float values into a thread-safe deque.
# The main thread drains this queue and processes windows.
# This ensures pyautogui.move() can NEVER block serial reading.

def serial_reader(ser, sample_queue, stop_event):
    while not stop_event.is_set():
        try:
            line = ser.readline()
        except Exception:
            break
        if not line:
            continue
        try:
            sample_queue.append(float(line.decode("utf-8", errors="ignore").strip()))
        except ValueError:
            continue


# ── MOUSE THREAD ──────────────────────────────────────────────────────────────
def mouse_mover(current_class_ref, stop_event):
    """Moves mouse every MOVE_EVERY_MS based on current prediction."""
    while not stop_event.is_set():
        cls = current_class_ref[0]
        if HAVE_PYAUTOGUI and cls in MOUSE_MOVE:
            dx, dy = MOUSE_MOVE[cls]
            try:
                pyautogui.move(dx, dy, duration=0)
            except Exception:
                pass
        time.sleep(MOVE_EVERY_MS / 1000.0)


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    port = pick_port()
    print(f"[INFO] Opening {port} @ 115200")
    ser = serial.Serial(port, 115200, timeout=1)
    time.sleep(0.5)
    ser.reset_input_buffer()

    model = load_model(BCI_MODEL) if BCI_MODEL else None
    if model is not None:
        print(f"[INFO] Streaming — 4-class model {BCI_MODEL}")
    else:
        print("[INFO] Streaming — binary linear only, no ML")
        print(f"  β < {BETA_THRESH}%  → Relax ↑   (mouse up)")
        print(f"  β ≥ {BETA_THRESH}%  → Focus ↓   (mouse down)")
    print()
    print("  δ%      θ%      α%      β%    raw   buf   → class")
    print("  " + "-" * 55)

    # Shared state
    sample_queue      = deque()          # filled by reader thread
    current_class_ref = [0]              # [0]=int, shared with mouse thread
    stop_event        = threading.Event()

    # Start background threads
    t_serial = threading.Thread(target=serial_reader,
                                args=(ser, sample_queue, stop_event), daemon=True)
    t_mouse  = threading.Thread(target=mouse_mover,
                                args=(current_class_ref, stop_event), daemon=True)
    t_serial.start()
    t_mouse.start()

    raw_buf = deque()
    d_pct = t_pct = a_pct = b_pct = 0.0
    last_print = time.monotonic()

    try:
        while True:
            # Drain everything the reader thread collected
            while sample_queue:
                raw_buf.append(sample_queue.popleft())

            # Process window when buffer is full
            if len(raw_buf) >= WIN:
                x   = np.asarray(raw_buf, dtype=np.float64)
                std = x.std()
                if std > 0.5 and x.max() < 1010 and x.min() > 10:
                    d_pct, t_pct, a_pct, b_pct = band_powers(x)
                    if model is not None:
                        current_class_ref[0] = int(model.predict([features(x)])[0])
                    else:
                        current_class_ref[0] = 0 if b_pct < BETA_THRESH else 1

                for _ in range(STEP):
                    raw_buf.popleft()

            # Print every second — always
            now = time.monotonic()
            if now - last_print >= 1.0:
                last_print = now
                raw_now  = raw_buf[-1] if raw_buf else 0
                buf_fill = min(100, int(len(raw_buf) / WIN * 100))
                cls      = current_class_ref[0]
                print(f"  δ={d_pct:6.1f}  θ={t_pct:6.1f}  α={a_pct:6.1f}"
                      f"  β={b_pct:6.1f}  raw={raw_now:4.0f}"
                      f"  buf={buf_fill:3d}%  → {CLASS_NAMES[cls]}")

            time.sleep(0.001)  # yield CPU; reader thread runs freely

    except KeyboardInterrupt:
        print("\n[INFO] Stopped.")
    finally:
        stop_event.set()
        try:
            ser.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
