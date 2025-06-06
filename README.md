# BCI - NeuroCursor
## A Non-Invasive BCI System for Multiclass Cursor Control Using Motor Imagery and the Emotiv Insight EEG Headset

## Abstract

**NeuroCursor** is an experimental Brain-Computer Interface (BCI) designed to empower individuals with **spastic tetraparesis** to control a digital interface via **imagined movement**. Using the **Emotiv Insight**, a consumer-grade wireless EEG headset, the system captures brain signals from **motor imagery** (the mental rehearsal of movement) and classifies them into **four distinct mental commands**. The system is a low-cost, non-invasive solution that aims to assist people with severe motor impairments by providing them with an alternative communication pathway. It consists of a modular pipeline for **signal acquisition**, **preprocessing**, **classification**, and **real-time cursor control**. This project is focused on accessibility, research, and neuroadaptive technology development.

---

## Motivation & Background

**Spastic tetraparesis** refers to a condition where an individual suffers from muscle weakness or paralysis in all four limbs, usually caused by damage to the **central nervous system (CNS)**. While these individuals are often unable to use their limbs for voluntary movement, **motor planning** and **cognitive functions** are generally unaffected. This **cognitive-motor dissociation** presents an opportunity for **assistive interfaces** that can bridge the gap between the cognitive and physical realms through **motor imagery**.

Motor imagery is the mental process of simulating movement without any physical action. It is well-documented that specific brain regions—such as the **sensorimotor cortex**—are activated during motor imagery. These regions can be captured non-invasively via **EEG** and processed for BCI applications.

**NeuroCursor** leverages this principle to create an accessible system for people with spastic tetraparesis, enabling them to control a virtual cursor and interact with digital interfaces. By utilizing the **Emotiv Insight EEG headset**, NeuroCursor presents an affordable, user-friendly, and scalable solution for those with mobility impairments.

### Inspiration

The idea for NeuroCursor was heavily inspired by Perri Karyal, a YouTube Streamer, who created a BCI interface to control a game using just their brain signals. The streamer was able to use motor imagery to perform game actions such as moving, aiming, and shooting, by thinking about specific body movements. Watching this demonstration highlighted the potential of BCI systems to transform how people with physical impairments could interact with the digital world, motivating the creation of a similar system to allow individuals with spastic tetraparesis to control a cursor in a virtual environment.

This innovative application of EEG technology in gaming opened my eyes to the vast possibilities in assistive technology, leading to the development of NeuroCursor, which aims to give users a simple yet powerful way to control digital interfaces.

Check out the original inspiration video from the streamer here: [BCI Game Control Demo]([url](https://www.youtube.com/shorts/Y1lSyrQJ2C4)).

---

## System Overview

### Classes of Mental Commands

The **NeuroCursor** BCI system is designed to classify brain signals into four mental commands corresponding to distinct imagined movements. These movements are thought to activate specific brain regions, which are then captured and classified by the EEG headset.

| Imagined Movement   | Command             | Purpose               |
|---------------------|---------------------|-----------------------|
| Left Hand           | `← Move Left`       | Move the cursor left  |
| Right Hand          | `→ Move Right`      | Move the cursor right |
| Left Foot           | `↑ Move Up`         | Move the cursor up    |
| Right Foot          | `↓ Move Down`       | Move the cursor down  |
| Tongue/Swallow      | `  Click`           | Click the cursor      |

### EEG Setup

- **Device**: [Emotiv Insight (5-channel wireless EEG headset)]([url](https://www.emotiv.com/products/insight))
- **Sampling Rate**: 256 Hz (optimal for detecting motor imagery signals)
- **Electrodes Used**: AF3, AF4, T7, T8, Pz (mapped to approximate C3, C4, Cz for sensory motor processing)
- **Sensor Type**: Semi-dry polymer electrodes
- **Software**: EmotivPRO + Cortex SDK (Python API)
- **Recording Length**: Each recording session lasts approximately 10 minutes per user

This setup captures the necessary brainwave patterns while minimizing user discomfort, thanks to the wireless design and ease of use of the **Emotiv Insight** headset.

---

## Signal Processing Pipeline

### 1. **Data Acquisition**
The EEG signals are streamed in real-time from the **Emotiv Insight** using the **Cortex SDK Python API**. During the data acquisition phase, users are presented with specific motor imagery tasks while visual stimuli (such as arrows) are displayed on the screen, indicating which movement to imagine. These visual cues are synchronized with EEG data to train the classifier.

### 2. **Preprocessing**
Raw EEG signals undergo several preprocessing steps to remove noise and ensure signal quality:

- **Bandpass Filter**: Frequencies between 8–30 Hz (capturing **Mu** and **Beta** rhythms associated with motor imagery)
- **Notch Filter**: 50 Hz filter to remove electrical noise from power lines
- **Epoching**: The EEG data is segmented into 4-second windows with a 50% overlap to preserve temporal information
- **Artifact Removal**: Techniques like **Independent Component Analysis (ICA)** and adaptive thresholding are used to remove artifacts from **eye blinks** and **muscle contractions**.

### 3. **Feature Extraction**
The processed data is then transformed into features that can be used by the classification algorithm:

- **Common Spatial Patterns (CSP)**: Used to extract spatial features from the EEG data, enhancing the separation of motor imagery classes.
- **Power Spectral Density (PSD)**: Calculated using the **Welch method** to estimate the power of different frequency bands.
- **Fast Fourier Transform (FFT)**: Helps identify frequency components within the motor imagery range.
- **Log-Variance and Band Power**: Calculated for motor-related bands (Mu and Beta) to quantify the brain activity during motor imagery tasks.

### 4. **Classification**
The extracted features are passed through a **Support Vector Machine (SVM)** classifier using a **one-vs-rest** strategy to classify the four commands. The SVM model is trained on offline data and validated through a **10-fold cross-validation** procedure. Initial classification accuracy ranges between 75–82%.

Future improvements are planned to involve more sophisticated models such as **Convolutional Neural Networks (CNN)** and **Long Short-Term Memory (LSTM)** networks to improve classification accuracy and allow for **subject-specific adaptation**.


## Software Architecture

```plaintext
  bci-neurocursor/
├── bci_controller.py         # Handles signal stream and event-based logic
├── signal_processing.py      # Includes filters, CSP, FFT, and artifact removal
├── model_training.py         # Offline training and testing of the classifier
├── virtual_cursor.py         # Integration with PyAutoGUI for OS-level mouse control
├── data/                     # EEG CSV files (real or synthetic for training)
├── docs/                     # Research paper, visuals, and reports
├── README.md
└── requirements.txt          # Python dependencies
```

## Integration of BioAmp with NeuroCursor

### BioAmp EXG Pill Integration

We’ve incorporated the **BioAmp EXG Pill** and **Muscle BioAmp Shield** from the **Upside Down Labs DIY Neuroscience Kit** into this project to provide additional signal acquisition capabilities. By using the **BioAmp EXG Pill**, we can record **EEG**, **EOG**, **EMG**, and **ECG** signals alongside the **Emotiv Insight**, creating a more comprehensive BCI system.
- **BioAmp EXG Pill**: A small, powerful analog front-end for recording biopotential signals.
- **Muscle BioAmp Shield**: Used to record muscle signals and can be integrated with the **Arduino** platform for real-time biofeedback.

### Setup and Usage:
1. **Hardware Setup**: The **BioAmp EXG Pill** is connected to the **Muscle BioAmp Shield** and an **Arduino UNO** for signal processing and visualization.
2. **Signal Integration**: Both devices send their data to a **Python** interface for analysis, enabling us to classify motor imagery from both **EEG (Emotiv)** and **EMG (BioAmp)** signals.
3. **Signal Fusion**: By combining **EEG** and **EMG** signals, we can improve control precision, enabling a more reliable and accurate **cursor control system**.


## Testing and Calibration

The system was calibrated using various mental tasks and motor imagery protocols. Adjustments to **thresholds**, **latency**, and **filter parameters** were made for optimal performance.

The integration of **BioAmp** sensors allowed for additional muscle signal control, while **Emotiv Insight** provided the primary **EEG** control for basic cursor movements. The combination of these signals allows for a robust and adaptive system that can respond to different user needs.


## References
- **Emotiv Insight**: [Emotiv Insight Official Site](https://www.emotiv.com/products/insight)
- **BioAmp EXG Pill**: [Upside Down Labs BioAmp Kit](https://store.upsidedownlabs.tech/)
- **Chords Python**: [Chords-Python GitHub](https://github.com/Chords-Python/)

