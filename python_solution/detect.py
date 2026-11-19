#!/Users/sorin/Documents/Repos/BCI/python_solution/.venv/bin/python
# -*- coding: utf-8 -*-
"""
EEG Band Power Calibration Tool (UNO R4 + BioAmp)

Records one state for 30 s (3 x 10 s segments) and prints band averages.

Usage:
    ./detect.py                  # prompts for state name
    ./detect.py "Jaw Pulse"      # state name as argument
"""

import os
import sys
import time
import warnings

import numpy as np
import serial
import serial.tools.list_ports as list_ports

warnings.filterwarnings("ignore")

# ================== CONFIG ==================
FS           = 512
FFT_SIZE     = 512      # 1 s per FFT window
SEGMENT_SECS = 10       # length of each segment
NUM_SEGMENTS = 3        # total = 30 s
COUNTDOWN    = 3

EPS = 1e-7

BANDS = ["delta", "theta", "alpha", "beta", "gamma"]
BAND_RANGES = {
    "delta": (0.5,  4.0),
    "theta": (4.0,  8.0),
    "alpha": (8.0,  13.0),
    "beta":  (13.0, 30.0),
    "gamma": (30.0, 45.0),
}


# ================== IIR BIQUAD ==================
class Biquad:
    __slots__ = ("sa1", "a2", "b0", "b1", "b2", "z1", "z2")

    def __init__(self, sa1, a2, b0, b1, b2):
        self.sa1 = sa1; self.a2 = a2
        self.b0  = b0;  self.b1 = b1; self.b2 = b2
        self.z1  = 0.0; self.z2 = 0.0

    def process(self, inp: float) -> float:
        w       = inp - self.sa1 * self.z1 - self.a2 * self.z2
        out     = self.b0 * w + self.b1 * self.z1 + self.b2 * self.z2
        self.z2 = self.z1
        self.z1 = w
        return out


def make_filters():
    notch1  = Biquad(-1.58696045, 0.96505858,  0.96588529, -1.57986211,  0.96588529)
    notch2  = Biquad(-1.62761184, 0.96671306,  1.00000000, -1.63566226,  1.00000000)
    eeg_lpf = Biquad(-1.24200128, 0.45885207,  0.05421270,  0.10842539,  0.05421270)
    return notch1, notch2, eeg_lpf


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
    return ports[0].device


# ================== BAND POWER ==================
def compute_band_powers(eeg_buf: np.ndarray) -> dict:
    fft_out = np.fft.rfft(eeg_buf)
    ps      = fft_out.real ** 2 + fft_out.imag ** 2
    bin_res = FS / len(eeg_buf)

    raw   = {name: 0.0 for name in BANDS}
    total = 0.0

    for i in range(1, len(ps)):
        freq   = i * bin_res
        p      = ps[i]
        total += p
        for name in BANDS:
            lo, hi = BAND_RANGES[name]
            if lo <= freq < hi:
                raw[name] += p
                break

    return {name: (raw[name] / (total + EPS)) * 100.0 for name in BANDS}


# ================== RECORD ONE SEGMENT ==================
def record_segment(ser, notch1, notch2, eeg_lpf, seg_num: int) -> dict:
    """Record SEGMENT_SECS of EEG. Returns per-band averages."""
    fft_buf = np.zeros(FFT_SIZE, dtype=np.float64)
    fft_idx = 0
    windows = []
    start   = time.monotonic()

    ser.reset_input_buffer()

    while time.monotonic() - start < SEGMENT_SECS:
        line = ser.readline()
        if not line:
            continue
        try:
            raw = float(line.decode("utf-8", errors="ignore").strip())
        except ValueError:
            continue

        s   = notch1.process(raw)
        s   = notch2.process(s)
        eeg = eeg_lpf.process(s)

        fft_buf[fft_idx] = eeg
        fft_idx += 1

        if fft_idx >= FFT_SIZE:
            fft_idx = 0
            pct       = compute_band_powers(fft_buf)
            windows.append(pct)
            elapsed   = time.monotonic() - start
            remaining = max(0.0, SEGMENT_SECS - elapsed)
            print(
                f"  [{seg_num}/{NUM_SEGMENTS}] t={elapsed:4.1f}s  "
                + "  ".join(f"{n}={pct[n]:5.1f}%" for n in BANDS)
                + f"  [{remaining:.0f}s left]"
            )

    if not windows:
        return {name: 0.0 for name in BANDS}
    return {name: float(np.mean([w[name] for w in windows])) for name in BANDS}


# ================== MAIN ==================
def main():
    if len(sys.argv) > 1:
        state = " ".join(sys.argv[1:])
    else:
        state = input("State name (e.g. 'Jaw Pulse', 'relax'): ").strip() or "state"

    port = pick_port()
    print(f"\n[INFO] Opening {port} @ 115200")
    ser = serial.Serial(port, 115200, timeout=1)

    print(f"\n  STATE: {state.upper()}  ({NUM_SEGMENTS} x {SEGMENT_SECS}s = {NUM_SEGMENTS * SEGMENT_SECS}s total)")
    for i in range(COUNTDOWN, 0, -1):
        print(f"  Get ready... {i}")
        time.sleep(1)
    print(f"  >> RECORDING — hold your state <<\n")

    notch1, notch2, eeg_lpf = make_filters()
    segments = []   # one dict per 10 s segment

    try:
        for seg in range(1, NUM_SEGMENTS + 1):
            avg = record_segment(ser, notch1, notch2, eeg_lpf, seg)
            segments.append(avg)
            print()
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted.")
    finally:
        ser.close()

    if not segments:
        return

    # ---- Results table ----
    overall = {name: float(np.mean([s[name] for s in segments])) for name in BANDS}

    # Header
    print(f"\n{state}")
    col = 8
    print(f"{'':8}" + "".join(f"{i+1:>{col}}" for i in range(len(segments))) + f"{'Avg':>{col}}")
    print("  " + "-" * (6 + col * (len(segments) + 1)))

    # One row per band
    for name in BANDS:
        row = f"{name:8}"
        for seg in segments:
            row += f"{seg[name]:>{col}.1f}"
        row += f"{overall[name]:>{col}.2f}"
        print(row)


if __name__ == "__main__":
    main()
