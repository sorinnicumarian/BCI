# Copyright (c) 2024 Umang Bansal
# 
# This software is the property of Umang Bansal. All rights reserved.
# Unauthorized copying of this file, via any medium, is strictly prohibited.
# Licensed under the MIT License. See the LICENSE file for details.

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt, iirnotch
import serial
import time

def setup_filters(sampling_rate):
    freq = 50  
    Q = 30 
    b_notch, a_notch = iirnotch(freq / (sampling_rate / 2), Q)

    low, high = 1, 40  
    b_band, a_band = butter(4, [low / (sampling_rate / 2), high / (sampling_rate / 2)], btype='band')

    return b_notch, a_notch, b_band, a_band

def process_data(data, b_notch, a_notch, b_band, a_band):
    data = filtfilt(b_notch, a_notch, data)  # Apply notch filter
    data = filtfilt(b_band, a_band, data)   # Apply bandpass filter
    return data

def calculate_features(data):
    energy = np.sum(np.square(data))
    zero_crossings = len(np.where(np.diff(np.signbit(data)))[0])
    return energy, zero_crossings

def main():
    ser = serial.Serial('COM5', 115200, timeout=1)
    sampling_rate = 512  
    b_notch, a_notch, b_band, a_band = setup_filters(sampling_rate)

    data_buffer = np.zeros(sampling_rate * 2)  
    plt.ion()  

    try:
        while True:
            line = ser.readline().decode().strip()
            if line:
                try:
                    value = float(line)
                    data_buffer[:-1] = data_buffer[1:]  
                    data_buffer[-1] = value  

                    if np.count_nonzero(data_buffer) == len(data_buffer):
                        processed_data = process_data(data_buffer.copy(), b_notch, a_notch, b_band, a_band)
                        energy, zero_crossings = calculate_features(processed_data)

                        # Plot data
                        #plt.clf()
                        #plt.plot(processed_data)
                        #plt.pause(0.05)

                        # Detection logic, adjust thresholds as necessary
                        if energy > 50000 and zero_crossings > 90:  # Example thresholds
                            print("Jaw clench detected")
                except ValueError:
                    print("Invalid data received:", line)
    finally:
        ser.close()
        plt.ioff()
        print("Serial port closed and plotting stopped.")

if __name__ == "__main__":
    main()
