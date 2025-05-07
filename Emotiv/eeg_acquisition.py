import emotiv
import time

class EEGAcquisition:
    def __init__(self):
        self.device = emotiv.Emotiv()
        self.device.open()
        
    def get_data(self, duration=10):
        # Start the data stream and collect EEG data for the given duration
        start_time = time.time()
        eeg_data = []
        
        while time.time() - start_time < duration:
            data = self.device.get_data()
            eeg_data.append(data)
        
        return eeg_data
    
    def close(self):
        self.device.close()