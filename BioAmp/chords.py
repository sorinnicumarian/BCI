# BioAmp Tool
# https://github.com/upsidedownlabs/BioAmp-Tool-Python
#
# Upside Down Labs invests time and resources providing this open source code,
# please support Upside Down Labs and open-source hardware by purchasing
# products from Upside Down Labs!
#
# Copyright (c) 2024 Payal Lakra
# Copyright (c) 2024 Upside Down Labs
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


# Import necessary modules
from pylsl import StreamInfo, StreamOutlet  # For LSL (Lab Streaming Layer) to stream data
import argparse  # For command-line argument parsing
import serial  # For serial communication with Arduino
import time  # For time-related functions
import csv  # For handling CSV file operations
from datetime import datetime  # For getting current timestamps
import serial.tools.list_ports  # To list available serial ports
import numpy as np  # For handling numeric arrays
import sys
import signal

# Initialize global variables for tracking and processing data
total_packet_count = 0  # Total packets received in the last second
cumulative_packet_count = 0  # Total packets received in the last 10 minutes
start_time = None  # Track the start time for packet counting
last_ten_minute_time = None  # Track the last 10-minute interval
previous_sample_number = None  # Store the previous sample number for detecting missing samples
missing_samples = 0  # Count of missing samples due to packet loss
buffer = bytearray()  # Buffer for storing incoming raw data from Arduino
samples_per_second = 0  # Number of samples received per second
retry_limit = 4

# Initialize gloabal variables for Arduino Board
board = ""          # Variable for Connected Arduino Board
supported_boards = {
    "UNO-R3": {"sampling_rate": 250, "Num_channels": 6},
    "UNO-CLONE": {"sampling_rate": 250, "Num_channels": 6},
    "GENUINO-UNO": {"sampling_rate": 250, "Num_channels": 6}, 
    "UNO-R4": {"sampling_rate": 500, "Num_channels": 6},
    "RPI-PICO-RP2040": {"sampling_rate": 500, "Num_channels": 3},
    "NANO-CLONE": {"sampling_rate": 250, "Num_channels": 8},
    "NANO-CLASSIC": {"sampling_rate": 250, "Num_channels": 8},
    "STM32F4-BLACK-PILL": {"sampling_rate": 500, "Num_channels": 8},
    "STM32G4-CORE-BOARD": {"sampling_rate": 500, "Num_channels": 16},
    "MEGA-2560-R3": {"sampling_rate": 250, "Num_channels": 16},
    "MEGA-2560-CLONE": {"sampling_rate": 250, "Num_channels": 16},
    "GIGA-R1": {"sampling_rate": 500, "Num_channels": 6},
    "NPG-LITE": {"sampling_rate": 500, "Num_channels": 3},
}

# Initialize gloabal variables for Incoming Data
SYNC_BYTE1 = 0xc7  # First byte of sync marker
SYNC_BYTE2 = 0x7c  # Second byte of sync marker
END_BYTE = 0x01  # End byte marker
HEADER_LENGTH = 3   #Length of the Packet Header

## Initialize gloabal variables for Output
lsl_outlet = None  # Placeholder for LSL stream outlet
verbose = False  # Flag for verbose output mode
csv_filename = None  # Store CSV filename
csv_file = None
ser = None
packet_length = None
num_channels = None

def connect_hardware(port, baudrate, timeout=1):
    try:
        ser = serial.Serial(port, baudrate=baudrate, timeout=timeout)  # Try opening the port
        response = None
        retry_counter = 0
        while response not in supported_boards and retry_counter < retry_limit:
            ser.write(b'WHORU\n') # Check board type
            try:
                response = ser.readline().strip().decode()  # Attempt to decode the response
            except UnicodeDecodeError as e:
                print(f"Decode error: {e}. Ignoring this response.")
                response = None
            retry_counter += 1
            if response in supported_boards:  # If response is received, assume it's the Arduino
                global board, sampling_rate, data, num_channels, packet_length
                board = response # Set board type
                print(f"{response} detected at {port} with baudrate {baudrate}.")  # Notify the user
                sampling_rate = supported_boards[board]["sampling_rate"]
                num_channels = supported_boards[board]["Num_channels"]
                packet_length = (2 * num_channels) + HEADER_LENGTH + 1
                data = np.zeros((num_channels, 2000))  # 2D array to store data for real-time plotting (num_channels, 2000 data points)
                if ser is not None:
                    return ser  # Return the port name
        ser.close()  # Close the port if no response
    except (OSError, serial.SerialException):  # Handle exceptions if the port can't be opened
        pass
    print(f"Unable to connect to any hardware at baudrate {baudrate}")  # Notify if no Arduino is found
    return None  # Return None if not found

def detect_hardware(baudrate=None, timeout=1):
    ports = serial.tools.list_ports.comports()  # List available serial ports
    ser = None
    baudrates = [baudrate] if baudrate else [230400, 115200]
    for port in ports:  # Iterate through each port
        for baud_rate in baudrates:  # Iterate through all baud rates
            print(f"Trying {port.device} at Baudrate {baud_rate}...")
            ser = connect_hardware(port.device, baud_rate, timeout)
            if ser is not None:
                return ser
    print("Unable to detect hardware!")  # Notify if no Arduino is found
    return None  # Return None if not found

def send_command(ser, command):
    ser.flushInput()   # Clear the input buffer
    ser.flushOutput()  # Clear the output buffer
    ser.write(f"{command}\n".encode())  # Send command
    time.sleep(0.1)  # Wait briefly to ensure Arduino processes the command
    response = ser.readline().decode('utf-8', errors='ignore').strip()  # Read response
    return response

# Function to read data from Arduino
def read_arduino_data(ser, csv_writer=None, inverted=False):
    global total_packet_count, cumulative_packet_count, previous_sample_number, missing_samples, buffer, data

    max_value = 2*10 if board == "UNO-R3" else 2*14
    min_value = 0
    mid_value = (max_value - 1) / 2
    
    raw_data = ser.read(ser.in_waiting or 1)  # Read available data from the serial port
    if raw_data == b'':
        send_command(ser, 'START')
    buffer.extend(raw_data)  # Add received data to the buffer
    while len(buffer) >= packet_length:  # Continue processing if the buffer contains at least one full packet
        sync_index = buffer.find(bytes([SYNC_BYTE1, SYNC_BYTE2]))  # Search for the sync marker

        if sync_index == -1:  # If sync marker not found, clear the buffer
            buffer.clear()
            continue
        
        if len(buffer) >= sync_index + packet_length:  # Check if a full packet is available
            packet = buffer[sync_index:sync_index + packet_length]  # Extract the packet
            if len(packet) == packet_length and packet[0] == SYNC_BYTE1 and packet[1] == SYNC_BYTE2 and packet[-1] == END_BYTE:
                if(start_time is None):
                    start_timer()  # Start timers for logging

                # Extract the packet if it is valid (correct length, sync bytes, and end byte)
                counter = packet[2]  # Read the counter byte (for tracking sample order)

                # Check for missing samples by comparing the counter values
                if previous_sample_number is not None and counter != (previous_sample_number + 1) % 256:
                    missing_samples += (counter - previous_sample_number - 1) % 256  # Calculate missing samples
                    if verbose:
                        print(f"Error: Expected counter {previous_sample_number + 1} but received {counter}. Missing samples: {missing_samples}")

                previous_sample_number = counter  # Update the previous sample number
                total_packet_count += 1  # Increment total packet count for the current second
                cumulative_packet_count += 1  # Increment cumulative packet count for the last 10 minutes

                # Extract channel data (num_channels, 2 bytes per channel)
                channel_data = []
                for channel in range(num_channels):  # Loop through channel data bytes
                    high_byte = packet[2*channel + HEADER_LENGTH]
                    low_byte = packet[2*channel + HEADER_LENGTH + 1]
                    value = (high_byte << 8) | low_byte  # Combine high and low bytes
                    if inverted:  # Apply inversion if the flag is set
                        if value > mid_value:
                            inverted_data = (mid_value) - abs(mid_value - value)
                        elif value < mid_value:
                            inverted_data = (mid_value) + abs(mid_value - value)
                        else:
                            inverted_data = value
                        channel_data.append(float(inverted_data))  # Append the inverted value
                    else:
                        channel_data.append(float(value))  # Convert to float and add to channel data

                if csv_writer:  # If CSV logging is enabled, write the data to the CSV file
                    csv_writer.writerow([counter] + channel_data)
                if lsl_outlet:  # If LSL streaming is enabled, send the data to the LSL stream
                    lsl_outlet.push_sample(channel_data)

                # Update the data array for real-time plotting
                data = np.roll(data, -1, axis=1)  # Shift data to the left
                data[:, -1] = channel_data  # Add new channel data to the right end of the array

                del buffer[:sync_index + packet_length]  # Remove the processed packet from the buffer
            else:
                del buffer[:sync_index + 1]  # If the packet is invalid, remove only the sync marker

# Function to start timers for logging data
def start_timer():
    global start_time, last_ten_minute_time, total_packet_count, cumulative_packet_count
    current_time = time.time()  # Get the current time
    start_time = current_time  # Set the start time for packet counting
    last_ten_minute_time = current_time  # Set the start time for 10-minute interval logging
    total_packet_count = 0  # Initialize total packet count
    cumulative_packet_count = 0  # Initialize cumulative packet count

# Function to log data every second
def log_one_second_data(verbose=False):
    global total_packet_count, samples_per_second
    samples_per_second = total_packet_count  # Update the samples per second
    if verbose:
        print(f"Data count for the last second: {total_packet_count} samples, Missing samples: {missing_samples}")  # Print verbose output
    total_packet_count = 0  # Reset total packet count for the next second

# Function to log data for 10-minute intervals
def log_ten_minute_data(verbose=False):
    global cumulative_packet_count, last_ten_minute_time
    if verbose:
        print(f"Total data count after 10 minutes: {cumulative_packet_count}")  # Print cumulative data count
        sampling_rate = cumulative_packet_count / (10 * 60)  # Calculate sampling rate
        print(f"Sampling rate: {sampling_rate:.2f} samples/second")  # Print sampling rate
        expected_sampling_rate = supported_boards[board]["sampling_rate"]  # Expected sampling rate
        drift = ((sampling_rate - expected_sampling_rate) / expected_sampling_rate) * 3600  # Calculate drift
        print(f"Drift: {drift:.2f} seconds/hour")  # Print drift
    cumulative_packet_count = 0  # Reset cumulative packet count
    last_ten_minute_time = time.time()  # Update the last 10-minute interval start time

# Main function to parse command-line arguments and handle data acquisition
def parse_data(ser, lsl_flag=False, csv_flag=False, verbose=False, run_time=None, inverted= False):
    global total_packet_count, cumulative_packet_count, start_time, lsl_outlet, last_ten_minute_time, csv_filename

    csv_writer = None  # Placeholder for CSV writer
    csv_file = None

    # Start LSL streaming if requested
    if lsl_flag:
        lsl_stream_info = StreamInfo('BioAmpDataStream', 'EXG', num_channels, supported_boards[board]["sampling_rate"], 'float32', 'UpsideDownLabs')  # Define LSL stream info
        lsl_outlet = StreamOutlet(lsl_stream_info)  # Create LSL outlet
        print("LSL stream started")  # Notify user
    
    if csv_flag:
        csv_filename = f"ChordsPy-{datetime.now().strftime('%Y%m%d-%H%M%S')}.csv"  # Create timestamped filename
        print(f"CSV recording started. Data will be saved to {csv_filename}")  # Notify user

    try:
        csv_file = open(csv_filename, mode='w', newline='') if csv_flag else None  # Open CSV file if logging is
        if csv_file:
            csv_writer = csv.writer(csv_file)  # Create CSV writer
            csv_writer.writerow([f"Arduino Board: {board}"])
            csv_writer.writerow([f"Sampling Rate (samples per second): {supported_boards[board]['sampling_rate']}"])
            csv_writer.writerow([])  # Blank row for separation
            csv_writer.writerow(['Counter'] + [f'Channel{i+1}' for i in range(num_channels)])  # Write header

        end_time = time.time() + run_time if run_time else None
        send_command(ser, 'START')

        while True:
            read_arduino_data(ser, csv_writer, inverted=inverted)  # Read and process data from Arduino
            if(start_time is not None):
                current_time = time.time()   # Get the current time
                elapsed_time = current_time - start_time   # Time elapsed since the last second
                elapsed_since_last_10_minutes = current_time - last_ten_minute_time  # Time elapsed since the last 10-minute interval

                if elapsed_time >= 1:  
                    log_one_second_data(verbose)
                    start_time = current_time

                if elapsed_since_last_10_minutes >= 600:
                    log_ten_minute_data(verbose) 

                if run_time and current_time >= end_time:
                    print("Runtime Over, sending STOP command...")
                    send_command(ser, 'STOP')
                    break

    except KeyboardInterrupt:
        print("Process interrupted by user")
    
    finally:
        cleanup()

    print(f"Total missing samples: {missing_samples}")
    sys.exit(0)

def cleanup():
    global ser, lsl_outlet, csv_file

    # Close the serial connection first
    try:
        if ser is not None and ser.is_open:
            send_command(ser, 'STOP')  # Ensure the STOP command is sent
            time.sleep(1)
            ser.reset_input_buffer()  # Clear the input buffer
            ser.reset_output_buffer()  # Clear the output buffer
            ser.close()  # Close the serial port
            print("Serial connection closed.")
        else:
            print("Serial connection is not open.")
    except Exception as e:
        print(f"Error while closing serial connection: {e}")

    # Close the LSL stream if it exists
    try:
        if lsl_outlet:
            print("Closing LSL Stream.")
            lsl_outlet = None  # Cleanup LSL outlet
    except Exception as e:
        print(f"Error while closing LSL stream: {e}")

    # Close the CSV file if it exists
    try:
        if csv_file:
            csv_file.close()  # Close the CSV file
            print("CSV recording saved.")
    except Exception as e:
        print(f"Error while closing CSV file: {e}")

    print("Cleanup completed, exiting program.")
    print(f"Total missing samples: {missing_samples}")
    sys.exit(0)

def signal_handler(sig, frame):
    cleanup()

# Main entry point of the script
def main():
    global verbose,ser
    parser = argparse.ArgumentParser(description="Upside Down Labs - Chords-Python Tool",allow_abbrev = False)  # Create argument parser
    parser.add_argument('-p', '--port', type=str, help="Specify the COM port")  # Port argument
    parser.add_argument('-b', '--baudrate', type=int, help="Set baud rate for the serial communication")  # Baud rate 
    parser.add_argument('--csv', action='store_true', help="Create and write to a CSV file")  # CSV logging flag
    parser.add_argument('--lsl', action='store_true', help="Start LSL stream")  # LSL streaming flag
    parser.add_argument('-v', '--verbose', action='store_true', help="Enable verbose output with statistical data")  # Verbose flag
    parser.add_argument('-t', '--time', type=int, help="Run the program for a specified number of seconds and then exit")   #set time
    parser.add_argument('--inverted', action='store_true', help="Invert the signal before streaming LSL and logging")  # Inverted flag

    args = parser.parse_args()  # Parse command-line arguments
    verbose = args.verbose  # Set verbose mode

    # Register the signal handler to handle Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    # Check if any logging or GUI options are selected, else show help
    if not args.csv and not args.lsl:
        parser.print_help()  # Print help if no options are selected
        return

    if args.port:
        print("trying to connect to port:", args.port)
        ser = connect_hardware(port=args.port, baudrate=args.baudrate)
    else:
        ser = detect_hardware(baudrate=args.baudrate)
        if ser is None:
            sys.stderr.write("Serial Connection not established properly.Try Again\n")
            sys.exit(1)  # Exit with a non-zero code to indicate failure
    if ser is None:
        print("Arduino port not specified or detected. Exiting.")  # Notify if no port is available
        return

    # Start data acquisition
    parse_data(ser, lsl_flag=args.lsl, csv_flag=args.csv, verbose=args.verbose, run_time=args.time, inverted=args.inverted)

# Run the main function if this script is executed
if __name__ == "__main__":
    main()