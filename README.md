
# Brain–Computer Interface (BCI) – EEG Attention & Relaxation Detection

## Table of Contents
1. **Introduction**
2. **Abbreviations & Core Concepts**
   - 2.1 FFT (Fast Fourier Transform)
   - 2.2 PSD (Power Spectral Density)
3. **Project Context: What This BCI Does**
4. **How EEG Signals Work (Simple Explanation)**
5. **EEG Frequency Bands & Mental States**
6. **Why the Alpha/Beta Ratio Matters**
7. **Machine Learning: SVM Explained Simply**
8. **End‑to‑End BCI Pipeline (Game Control Flow)**
9. **Arduino Hardware Setup**
10. **Arduino Software Setup**
11. **Arduino Test Procedures**
    - 11.1 Test 1.0 – Board Functionality
    - 11.2 Test 1.1 – Sensor Reading
    - 11.3 Test 1.2 – EEG Filtering Verification
    - 11.4 Test 1.3 – FFT & Band Percentage Output
12. **Prediction Feature Statistics (Model Input)**
13. **Interpreting the Feature Statistics**
14. **License**

---

# 1. Introduction
This repository contains a functional **Brain–Computer Interface (BCI)** built using:
- **BioAmp EXG Pill** (EEG acquisition)
- **Arduino UNO R4** (signal preprocessing and streaming)
- **Python (FFT, PSD, SVM)** (feature extraction & classification)

The system classifies two mental states:
- **Focus / Attention** → Beta activity increases
- **Relaxation / Calmness** → Alpha activity increases

The classifier output is used to control a **car game** without physical input.

---

# 2. Abbreviations & Core Concepts
## 2.1 FFT — Fast Fourier Transform
FFT answers the question:
> "Instead of showing me the signal in time, show me how much of each frequency it contains."

Analogy:
- A music chord is made of multiple notes.
- FFT tells you which notes are inside.

For EEG:
- **Alpha = 8–13 Hz** (relaxed)
- **Beta = 13–30 Hz** (focused)

## 2.2 PSD — Power Spectral Density
FFT shows *which* frequencies exist.  
PSD shows *how strong* each frequency is.

Analogy:
- FFT → notes in a song
- PSD → loudness of each note

This helps answer:
- "Is alpha strong?" → relaxation
- "Is beta strong?" → concentration

---

# 3. Project Context
This BCI demonstrates how EEG signals can be used to:
- Detect **attentive** vs **relaxed** mental states
- Control a game **hands‑free**
- Provide real‑time neurofeedback


---

# 4. How EEG Signals Work (Simple Explanation)
The Arduino reads values **around ~512** (middle of its 0–1023 ADC range).

A single value (e.g., 519) doesn’t tell you anything. What matters is the **pattern over time**:

- Fast wiggles → **Beta waves** → Focus
- Slow wiggles → **Alpha waves** → Relaxation


---

# 5. EEG Frequency Bands & Meanings
| Band  | Hz Range | Meaning |
|-------|----------|---------|
| Delta | 0.5–3 Hz | Deep sleep |
| Theta | 3–8 Hz | Drowsy / Daydreaming |
| Alpha | 8–13 Hz | Relaxed but awake |
| Beta  | 13–30 Hz | Focus / mental effort |

Gamma is ignored because low‑cost electrodes can’t capture it reliably.

---

# 6. Why the Alpha/Beta Ratio?
A simple and reliable indicator:
```
alpha_beta_ratio = alpha_power / beta_power
```
Interpretation:
- **High ratio → relaxed**
- **Low ratio → focused**

Used to drive in‑game actions:
- Focus → accelerate
- Relax → stop braking / idle

---

# 7. Machine Learning: SVM (Simple Explanation)
An **SVM** finds the best line separating two groups.

Imagine plotting:
- X‑axis = alpha power
- Y‑axis = beta power

Relaxed points cluster together.  
Focused points cluster elsewhere.  
SVM draws the optimal boundary.

---

# 8. End‑to‑End BCI Pipeline (Game Control Flow)
1. Arduino reads EEG voltage continuously
2. Arduino applies digital filters:
   - 50 Hz notch
   - 0.5–30 Hz band‑pass
3. Python receives filtered samples
4. Python computes PSD using Welch method
5. Features extracted:
   - Alpha power
   - Beta power
   - Theta/Delta
   - Alpha/Beta ratio
   - Spectral centroid
   - Peak frequency
   - Spectral slope
6. SVM performs classification
7. Game receives commands:
   - Focus → "move"
   - Relax → "stop"

---

# 9. Arduino Hardware Installation
1. Connect Arduino board to PC via USB
2. Connect EEG electrodes to BioAmp EXG Pill
3. Wire BioAmp → Arduino:
   - VCC → 5V
   - GND → GND
   - OUT → A0

Diagram: `artefacts/images/connection_bioamp_exg_pill_to_arduino.png`

---

# 10. Arduino Software Setup
1. Install the **Arduino IDE**
2. Upload test sketches from the `arduino_tests/` folder

---

# 11. Arduino Test Procedures
## 11.1 Test 1.0 — Board Test
- Ensure Serial communication works.

## 11.2 Test 1.1 — Sensor Read Test
- Values should fluctuate around **450–600** (center ≈ 512)

## 11.3 Test 1.2 — EEG Filter Test
Purpose: verify that only useful EEG frequencies remain.

**Pass-band:** 0.5–30 Hz  
**Stop-band:** <0.5 Hz, >30 Hz, and 50 Hz mains

Expected filtered signal:
- Centered near **512**
- No clipping
- Stable fluctuations in **450–600** range

A “PASS” is confirmed when the signal shows stable fluctuations around 512, without clipping (0 or 1023) and without drifting out of range.

## 11.4 Test 1.3 — BCI FFT Test
Arduino should:
- Sample at 500–512 Hz
- Filter signal
- Perform FFT every N samples
- Output: `delta%, theta%, alpha%, beta%, gamma%` (sum ≈ 100%)

---

# Python Solution Install
```
cd python_solution
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt                                         
python3 predict.py
```

# 12. Prediction Feature Statistics (Example)
```
E_alpha            mean: 5.23
E_beta             mean: 11.23
E_theta            mean: 5.38
E_delta            mean: 9.54
alpha/beta ratio   mean: 0.63
peak_frequency     mean: 7.36 Hz
spectral_centroid  mean: 11.38 Hz
spectral_slope     mean: -10.79
```

---

# 13. Interpreting Feature Statistics
### Healthy indicators:
- Balanced class distribution
- Alpha/Beta ratio around 0.6
- Spectral centroid around 10–12 Hz

### Red Flags (Require Fixes):
**1. `peak_frequency = 0 Hz`** → Should not happen after proper filtering.

**2. `spectral_slope ≈ -10`** → EEG slopes should be ~−1 to −2. Fit only within 2–30 Hz.

**3. Huge Delta/Theta values** → Motion or eye‑blink artifacts. You must reject noisy windows.

---

# 14. License
This project is licensed under the MIT License.

# Experience

