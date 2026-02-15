# bci_controller.py

from eeg_acquisition import EEGAcquisition
from model_training import ModelTraining
from virtual_cursor import VirtualCursor
import time

class BCICursorControl:
    def __init__(self):
        self.eeg_acquisition = EEGAcquisition()
        self.model_training = ModelTraining()
        self.virtual_cursor = VirtualCursor()
    
    def run(self, duration=10):
        print("Starting EEG acquisition...")
        eeg_data = self.eeg_acquisition.get_data(duration)
        
        print("Training the model with acquired data...")
        # Simulate labels as random for demonstration
        labels = [0, 1, 2, 3] * (len(eeg_data) // 4)
        self.model_training.train(eeg_data, labels)
        
        print("Ready for real-time cursor control...")
        for i in range(duration):
            data = self.eeg_acquisition.get_data(1)
            command = self.model_training.classify(data)
            self.execute_command(command)
            time.sleep(1)
    
    def execute_command(self, command):
        if command == 0:
            self.virtual_cursor.move_cursor('left')
        elif command == 1:
            self.virtual_cursor.move_cursor('right')
        elif command == 2:
            self.virtual_cursor.move_cursor('up')
        elif command == 3:
            self.virtual_cursor.move_cursor('down')
        elif command == 4:
            self.virtual_cursor.click()
        elif command == 5:
            self.virtual_cursor.backspace()

if __name__ == "__main__":
    bci_controller = BCICursorControl()
    bci_controller.run(duration=10)