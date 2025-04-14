# BCI Virtual Keyboard Control for Tetraparesis using Emotiv Insight
# Author: Sorin Nicu Marian
# Repository: https://github.com/YOUR_USERNAME/bci-insight-tetraparesis
# Description: Simulated codebase for a BCI system using Emotiv Insight to control a virtual keyboard

import time
import random

class SimulatedEEGDevice:
    """
    Simulates EEG data from Emotiv Insight headset.
    Replace with real Emotiv Cortex SDK integration when hardware is available.
    """
    def __init__(self):
        self.channels = ['AF3', 'T7', 'Pz', 'T8', 'AF4']  # Simulated channels

    def connect(self):
        print("[INFO] Connecting to Emotiv Insight (simulated)...")
        time.sleep(1)
        print("[INFO] Connected.")

    def get_data(self):
        """ Simulate EEG data sample as a list of 5 channel values """
        return [random.uniform(-100, 100) for _ in self.channels]


class MotorImageryClassifier:
    """
    Simulates a classifier that detects imagined left vs. right hand movement.
    Replace with trained ML model using actual EEG data.
    """
    def predict(self, eeg_data):
        feature_sum = sum(eeg_data)
        return 'left' if feature_sum < 0 else 'right'


class VirtualKeyboardController:
    """
    Simulates a virtual keyboard controlled by motor imagery.
    """
    def move_cursor(self, direction):
        if direction == 'left':
            print("[KEYBOARD] Cursor moved left")
        elif direction == 'right':
            print("[KEYBOARD] Cursor moved right")

    def click(self):
        print("[KEYBOARD] Click action triggered")


def main():
    eeg_device = SimulatedEEGDevice()
    classifier = MotorImageryClassifier()
    keyboard = VirtualKeyboardController()

    eeg_device.connect()

    print("[SYSTEM] Starting BCI control loop... Press Ctrl+C to stop.")
    try:
        while True:
            data = eeg_device.get_data()
            direction = classifier.predict(data)
            keyboard.move_cursor(direction)
            if random.random() < 0.1:
                keyboard.click()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[SYSTEM] Stopping BCI system.")


if __name__ == "__main__":
    main()
