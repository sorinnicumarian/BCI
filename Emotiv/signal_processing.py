# signal_processing.py

import numpy as np
from sklearn.decomposition import FastICA
from scipy.signal import butter, lfilter
from sklearn.preprocessing import StandardScaler

class SignalProcessing:
    def __init__(self, sampling_rate=256, bandpass_range=(8, 30), notch_freq=50):
        self.sampling_rate = sampling_rate
        self.bandpass_range = bandpass_range
        self.notch_freq = notch_freq
        
    def bandpass_filter(self, data, low, high):
        # Apply bandpass filter between low and high frequencies
        nyquist = 0.5 * self.sampling_rate
        low = low / nyquist
        high = high / nyquist
        b, a = butter(4, [low, high], btype='band')
        return lfilter(b, a, data)
    
    def notch_filter(self, data, freq):
        # Apply notch filter to remove 50 Hz mains noise
        nyquist = 0.5 * self.sampling_rate
        freq = freq / nyquist
        b, a = butter(4, freq, btype='bandstop')
        return lfilter(b, a, data)
    
    def artifact_removal(self, data):
        # Perform ICA for artifact removal
        ica = FastICA(n_components=len(data))
        return ica.fit_transform(data)
    
    def preprocess(self, eeg_data):
        # Apply preprocessing steps
        data_filtered = self.bandpass_filter(eeg_data, *self.bandpass_range)
        data_notch_filtered = self.notch_filter(data_filtered, self.notch_freq)
        return data_notch_filtered
    
    def extract_features(self, eeg_data):
        # Extract features: CSP, band power, etc.
        features = []
        # Example feature extraction using band power
        band_powers = self.compute_band_powers(eeg_data)
        features.extend(band_powers)
        return np.array(features)
    
    def compute_band_powers(self, data):
        # Example function to compute band power
        bands = {'mu': (8, 13), 'beta': (13, 30)}
        powers = []
        for band, (low, high) in bands.items():
            band_data = self.bandpass_filter(data, low, high)
            powers.append(np.mean(band_data**2))
        return powers