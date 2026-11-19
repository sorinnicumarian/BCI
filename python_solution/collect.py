#!/Users/sorin/Documents/Repos/BCI/python_solution/.venv/bin/python
"""
collect.py — Raw EEG data collector for BioAmp EXG Pill + Arduino UNO R4

Usage:
    ./collect.py <state_name>          # e.g. ./collect.py 08_relax_up
    ./collect.py <state_name> <secs>   # e.g. ./collect.py 08_relax_up 120

Saves to: ../artefacts/data/<state_name>.csv
Requires: signal.ino uploaded (512 Hz raw ADC, no filters)
"""
import sys
import csv
import time
import os
import serial
import serial.tools.list_ports as list_ports
import select

BAUD_RATE   = 115200
SAMPLE_RATE = 512
DEFAULT_SECS = 120

EXCLUDE = ("bluetooth", "bt-", "debug")

# ── output path ──────────────────────────────────────────────────────────────
def resolve_path(name):
    script_dir  = os.path.dirname(os.path.abspath(__file__))
    data_dir    = os.path.join(script_dir, '..', 'artefacts', 'data')
    os.makedirs(data_dir, exist_ok=True)
    fname = name if name.endswith('.csv') else name + '.csv'
    return os.path.abspath(os.path.join(data_dir, fname))

# ── port selection ────────────────────────────────────────────────────────────
def pick_port():
    ports = list(list_ports.comports())
    if not ports:
        raise RuntimeError("No serial ports found.")

    # 1. UNO R4 native USB
    for p in ports:
        if 'usbmodem' in p.device.lower():
            return p.device

    # 2. Any USB serial, excluding Bluetooth
    for p in ports:
        dev = p.device.lower()
        if dev.startswith('/dev/cu.usb') and not any(x in dev for x in EXCLUDE):
            return p.device

    # 3. Fallback — skip Bluetooth
    for p in ports:
        if not any(x in p.device.lower() for x in EXCLUDE):
            return p.device

    raise RuntimeError("No suitable port found (only Bluetooth detected?).")

# ── main ──────────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print("Usage: ./collect.py <state_name> [seconds]")
        print("  e.g. ./collect.py 08_relax_up")
        print("  e.g. ./collect.py 08_relax_up 120")
        sys.exit(1)

    state_name  = sys.argv[1]
    duration    = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_SECS
    out_path    = resolve_path(state_name)

    # Warn if file already exists
    if os.path.exists(out_path):
        ans = input(f"[WARN] {out_path} already exists. Overwrite? [y/N] ").strip().lower()
        if ans != 'y':
            print("Aborted.")
            sys.exit(0)

    port = pick_port()
    print(f"[INFO] Port    : {port} @ {BAUD_RATE} baud")
    print(f"[INFO] Output  : {out_path}")
    print(f"[INFO] Duration: {duration}s  (~{duration * SAMPLE_RATE} samples)")
    print()

    try:
        ser = serial.Serial(port, BAUD_RATE, timeout=1)
    except serial.SerialException as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    time.sleep(2.0)          # wait for Arduino reset
    ser.reset_input_buffer()

    n_samples = 0

    try:
        with open(out_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['index', 'value'])   # header

            print(f">>> Recording '{state_name}' — hold your state!")
            print("    Press ENTER to stop early.\n")

            start     = time.time()
            last_print = start

            while True:
                # stop on ENTER
                rlist, _, _ = select.select([sys.stdin], [], [], 0.0)
                if rlist and sys.stdin.readline().strip() == '':
                    print("\n[INFO] Stopped early.")
                    break

                # time limit
                elapsed = time.time() - start
                if elapsed >= duration:
                    print("\n[INFO] Done.")
                    break

                # countdown every second
                if time.time() - last_print >= 1.0:
                    remaining = max(0, duration - int(elapsed))
                    bar_len   = 30
                    filled    = int(bar_len * elapsed / duration)
                    bar       = '█' * filled + '░' * (bar_len - filled)
                    print(f"\r  [{bar}] {remaining:3d}s left  |  {n_samples} samples", end='', flush=True)
                    last_print = time.time()

                # read serial
                try:
                    raw = ser.readline()
                except serial.SerialException as e:
                    print(f"\n[WARN] Serial error: {e}")
                    continue

                if raw:
                    line = raw.decode('utf-8', errors='ignore').strip()
                    if line:
                        try:
                            int(line)   # validate it's a number
                        except ValueError:
                            continue
                        writer.writerow([n_samples, line])
                        n_samples += 1

    except KeyboardInterrupt:
        print("\n[INFO] Stopped by Ctrl+C.")
    finally:
        ser.close()

    os.system('afplay /System/Library/Sounds/Glass.aiff')
    print(f"\n[OK] Saved {n_samples} samples → {out_path}")
    expected = duration * SAMPLE_RATE
    if n_samples < expected * 0.9:
        print(f"[WARN] Expected ~{expected} samples at {SAMPLE_RATE} Hz — got {n_samples}.")
        print("       Check that signal.ino is uploaded (not a slower sketch).")

if __name__ == '__main__':
    main()
