#!/Users/sorin/Documents/Repos/BCI/python_solution/.venv/bin/python
import sys
import csv
import time
import datetime as dt
import serial
import serial.tools.list_ports as list_ports
import os
import select  # POSIX: macOS/Linux non-blocking stdin

BAUD_RATE = 115200
CSV_PATH = 'signal.csv'
MAX_SECONDS = 300  # None = no time limit; or set e.g. 300 for 5 minutes

def pick_port():
    ports = list(list_ports.comports())
    if not ports:
        raise RuntimeError("No serial ports found. Is the board connected and powered?")

    # Prefer native USB CDC ACM devices (UNO R4 appears as 'usbmodem')
    for p in ports:
        dev = p.device
        if 'usbmodem' in dev.lower():
            return dev

    # Fallback to any cu.usb* device
    for p in ports:
        dev = p.device
        if dev.startswith('/dev/cu.usb'):
            return dev

    # Last resort: first port
    return ports[0].device

def main():
    # Resolve port
    port = pick_port()
    print(f"[INFO] Opening {port} @ {BAUD_RATE}")

    try:
        ser = serial.Serial(port, BAUD_RATE, timeout=1)
    except serial.SerialException as e:
        print(f"[ERROR] Failed to open {port}: {e}")
        sys.exit(1)

    try:
        # Allow board reset on open
        time.sleep(2.0)
        ser.reset_input_buffer()

        # Open CSV and write header if new
        file_exists = os.path.exists(CSV_PATH)
        with open(CSV_PATH, 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists or os.path.getsize(CSV_PATH) == 0:
                writer.writerow(['timestamp', 'value'])

            print("[INFO] Collecting data...")
            print("[INFO] Press ENTER to stop")
            if MAX_SECONDS:
                print(f"[INFO] Auto-stop after {MAX_SECONDS} seconds.")

            start = time.time()

            # --- Per-second print state ---
            last_print_sec = int(time.time())
            last_line_in_sec = None  # store the latest valid line within the current second

            while True:
                # 1) Stop on ENTER (empty line)
                rlist, _, _ = select.select([sys.stdin], [], [], 0.0)
                if rlist:
                    user_line = sys.stdin.readline().strip()
                    if user_line == '':
                        print("[INFO] Stop command received.")
                        break

                # Optional time cap
                if MAX_SECONDS is not None and (time.time() - start) >= MAX_SECONDS:
                    print("[INFO] Reached time limit. Stopping.")
                    break

                # 2) Read serial line (non-blocking via timeout=1)
                try:
                    raw = ser.readline()
                except serial.SerialException as e:
                    print(f"[WARN] Serial read error: {e}")
                    continue

                if raw:
                    try:
                        line = raw.decode('utf-8', errors='ignore').strip()
                    except Exception:
                        line = raw.decode('latin-1', errors='ignore').strip()

                    if line:
                        # Write to CSV
                        ts = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
                        writer.writerow([ts, line])

                        # Update the "latest this second"
                        last_line_in_sec = line

                # 3) Once per second, print the latest line seen in that second
                now_sec = int(time.time())
                if now_sec != last_print_sec:
                    if last_line_in_sec is not None:
                        # Print to stdout with a timestamp
                        ts_print = dt.datetime.now().strftime('%H:%M:%S')
                        print(f"[{ts_print}] {last_line_in_sec}")
                        last_line_in_sec = None  # reset for the new second
                    last_print_sec = now_sec

    except KeyboardInterrupt:
        print("\n[INFO] Stopped by user (Ctrl+C).")
    finally:
        try:
            ser.close()
            print("[INFO] Serial port closed.")
        except Exception:
            pass

if __name__ == "__main__":
    main()