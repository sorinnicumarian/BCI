# model_training.py

import numpy as np
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from signal_processing import SignalProcessing

class ModelTraining:
    def __init__(self, classifier=SVC(kernel='linear')):
        self.classifier = classifier
        self.signal_processor = SignalProcessing()

    def train(self, eeg_data, labels):
        # Feature extraction and training the model
        features = [self.signal_processor.extract_features(data) for data in eeg_data]
        features = np.array(features)
        
        # Standardize the features
        scaler = StandardScaler()
        features = scaler.fit_transform(features)
        
        # Split data into training and test sets
        X_train, X_test, y_train, y_test = train_test_split(features, labels, test_size=0.2, random_state=42)
        
        # Train the model
        self.classifier.fit(X_train, y_train)
        
        # Evaluate the model
        y_pred = self.classifier.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        print(f"Model accuracy: {accuracy * 100:.2f}%")
        return self.classifier
    
    def classify(self, eeg_data):
        # Predict using the trained classifier
        features = self.signal_processor.extract_features(eeg_data)
        features = np.array(features).reshape(1, -1)  # Reshape to match expected input
        return self.classifier.predict(features)[0]