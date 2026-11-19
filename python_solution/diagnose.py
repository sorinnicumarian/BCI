#!/Users/sorin/Documents/Repos/BCI/python_solution/.venv/bin/python
"""
diagnose.py — Check Arduino serial rate and raw signal stats.
Run this before predict.py to verify hardware is sending data correctly.
"""
import serial
import serial.tools.list_ports as list_ports
import time
import os

BAUD = 115200
DURATION = 5  # seconds to sample

def pick_port():
    env = os.environ.get("BCI_PORT")
    if env:
        return env
    ports = list(list_ports.comports())
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
    raise RuntimeError("No Arduino port found. Connect the device and retry.")

port = pick_port()
print(f"Port : {port}")
print(f"Sampling {DURATION}s at {BAUD} baud...\n")

ser = serial.Serial(port, BAUD, timeout=1)
time.sleep(0.5)  # let Arduino reset

samples = []
t0 = time.monotonic()
while time.monotonic() - t0 < DURATION:
    line = ser.readline()
    if not line:
        continue
    try:
        samples.append(float(line.decode("utf-8", errors="ignore").strip()))
    except ValueError:
        pass
ser.close()

if not samples:
    print("ERROR: No numeric data received. Check cable / sketch.")
else:
    import numpy as np
    arr = np.array(samples)
    hz  = len(arr) / DURATION
    print(f"Samples received : {len(arr)}")
    print(f"Effective rate   : {hz:.1f} Hz  (expected ~512)")
    print(f"Value range      : min={arr.min():.0f}  max={arr.max():.0f}  (ADC 0-1023)")
    print(f"Mean / Std       : {arr.mean():.1f} / {arr.std():.1f}")
    print()
    if hz < 400:
        print("⚠  Rate too low — sketch may not be running at 512 Hz.")
    elif arr.max() > 1000 or arr.min() < 20:
        print("⚠  Values near ADC rail — check electrode polarity.")
    elif arr.std() < 1:
        print("⚠  Signal is flat — electrode disconnected?")
    else:
        print("✓  Signal looks healthy. You can run predict.py.")
