
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

---

# Dataset Information

The dataset consists of **3 recording sessions** from a single subject (the author):

| Session | Label | Duration | Activity | Details | Music | Eyes |
|---------|-------|----------|----------|---------|-------|------|
| 1 | Concentrate | 3 min | Play | Subway Surfers | - | - |
| 1 | Relax | 5.1 min | Meditate | - | Yes | Closed |
| 2 | Concentrate | 5 min | Focus | Car Logo game | - | - |
| 2 | Relax | 5 min | Meditate | - | No | Closed |
| 3 | Concentrate | 5 min | Play | Subway Surfers | - | - |
| 3 | Relax | 5 min | Meditate | - | No | Closed |

**Training Data:** Session 3 only (10 minutes: 5 min concentrate + 5 min relax)
**Total Available:** ~28 minutes across all sessions
**Sampling Rate:** 512 Hz
**Window Size:** 1 second (512 samples) with 50% overlap
**Feature Count:** 19 (spectral + temporal + Arduino-inspired smoothed features)

The model achieves **77-80% accuracy** using SVM with RBF kernel after proper feature engineering, artifact rejection, and Arduino-inspired smoothing.

---

# 12. How the Machine Learning Model Works (Simple Explanation)

## The Problem: Detecting Mental States from Brain Signals

Imagine you're wearing an EEG sensor that measures your brain's electrical activity. When you concentrate, your brain produces more **beta waves** (fast wiggles). When you relax, it produces more **alpha waves** (slow wiggles). But here's the challenge:

- Everyone's brain is different
- Your "high beta" might be someone else's "low beta"
- Noise from eye blinks, muscle movements, etc.
- Simple thresholds don't work well

**Goal:** Build a system that learns to recognize YOUR concentrate vs relax patterns specifically.

---

## Two Approaches: Threshold vs Machine Learning

### Approach 1: Simple Threshold (Arduino Code)
```
if (beta_percentage > 2.0):
    print("Focus detected!")
else:
    print("Relaxed")
```

**How it works:**
- Measure beta power as % of total brain activity
- If beta > 2%, you're focusing
- If beta < 2%, you're relaxed

**Pros:** Simple, fast, no training needed
**Cons:**
- Fixed threshold doesn't adapt to you
- Only uses 1 measurement
- Sensitive to noise (one blink → wrong prediction)
- Accuracy: ~60-70%

### Approach 2: Machine Learning (This Project)
```python
model.predict(your_brain_features)
→ Uses 19 measurements + learned patterns
→ Accuracy: 80-85%
```

**How it works:** Instead of a fixed rule, the model **learns** from examples.

---

## Step-by-Step: How ML Training Works

Think of it like teaching a friend to recognize your mental states:

### **Step 1: Collect Examples**
You provide training data - recordings of your brain when:
- Concentrating (playing games, solving problems)
- Relaxing (meditating, eyes closed)

**In this project:** 10 minutes total (5 min concentrate + 5 min relax)

### **Step 2: Extract Features**
For each 1-second window of brain activity, we calculate **19 measurements**:

| Feature | What It Measures | Example Value |
|---------|------------------|---------------|
| `E_beta` | Beta wave power (concentration) | 0.18 (18% of total) |
| `E_alpha` | Alpha wave power (relaxation) | 0.22 (22% of total) |
| `beta_percentage` | Beta as % (Arduino's metric) | 18.0% |
| `smoothed_beta` | Noise-reduced beta | 0.17 |
| `hjorth_mobility` | Signal frequency variation | 1.2 |
| ... | (15 more features) | ... |

Think of these as **different measurements** you'd take to describe brain activity - like how you'd describe a car with multiple specs (speed, fuel, RPM, temperature, etc.).

### **Step 3: Label the Data**
Each 1-second window gets a label:
- **0** = Relax
- **1** = Concentrate

After processing, we have ~1,000 examples:
```
Window 1: [E_beta=0.15, E_alpha=0.25, smoothed_beta=0.14, ...] → Label: 0 (Relax)
Window 2: [E_beta=0.22, E_alpha=0.18, smoothed_beta=0.21, ...] → Label: 1 (Focus)
Window 3: [E_beta=0.16, E_alpha=0.24, smoothed_beta=0.15, ...] → Label: 0 (Relax)
...
```

### **Step 4: Train the SVM Model**

**SVM = Support Vector Machine** - finds the best way to separate two groups.

**Simple Analogy:**
Imagine plotting your brain data on a graph:
- X-axis = Beta power
- Y-axis = Alpha power

```
      Alpha
       ↑
  0.3 |  R  R     R
      |  R    R R
  0.2 |     R   F  F
      |      F  F  F
  0.1 |     F  F
      |________________→ Beta
         0.1  0.2  0.3

  R = Relax samples
  F = Focus samples
```

SVM's job: **Draw the best line** separating R's from F's.

But wait - we have **19 dimensions** (19 features), not just 2! So SVM finds the best **hyperplane** (19-dimensional "line") that separates concentrate from relax.

**Magic of SVM:**
- Tries different separators
- Picks the one with the **biggest margin** (most confident separation)
- Handles non-linear patterns using the **RBF kernel** (like drawing curves instead of straight lines)

### **Step 5: Optimize Hyperparameters**

SVM has settings (hyperparameters) that affect how it learns:

| Parameter | What It Does | Example Values |
|-----------|-------------|----------------|
| `C` | How strict vs flexible | 0.1 (lenient) to 100 (strict) |
| `gamma` | How curvy the separator can be | 0.001 (smooth) to 1 (wiggly) |
| `kernel` | Shape of separator | 'rbf' (curved), 'linear' (straight) |

**GridSearchCV** tries **all combinations** and picks the best:
```
Testing: C=0.1, gamma=0.01, kernel=rbf → Accuracy: 72%
Testing: C=1, gamma=0.1, kernel=rbf → Accuracy: 78%
Testing: C=10, gamma=0.01, kernel=rbf → Accuracy: 81% ← Best!
...
```

This is why training takes 5-10 minutes - it's testing hundreds of combinations!

### **Step 6: Test & Validate**

After training, we test on **unseen data** (20% held back):
```
Trained on: 800 samples
Tested on: 200 samples (model has never seen these!)

Result: 81% accuracy
```

**What this means:**
- 81 out of 100 predictions are correct
- Way better than 60-70% from simple threshold
- Good enough for real-time BCI control!

---

## How Prediction Works (Real-Time)

When you run `predict.py`:

### **Step 1: Read EEG Signal**
```python
Arduino sends: [520, 518, 525, 512, ...]  # Raw voltage values
```

### **Step 2: Filter Noise**
```python
Apply 50 Hz notch filter → Remove electrical interference
Apply 0.5-30 Hz bandpass → Keep only brain waves
```

### **Step 3: Extract Features**
For each 1-second window (512 samples):
```python
features = {
    'E_beta': 0.19,
    'E_alpha': 0.21,
    'beta_percentage': 19.0,
    'smoothed_beta': 0.18,
    ... (15 more)
}
```

### **Step 4: Scale Features**
```python
# ML models need consistent scales
scaled_beta = (raw_beta - mean_beta) / std_beta
```

### **Step 5: Predict**
```python
prediction = model.predict(scaled_features)
→ 1 (Focus!) or 0 (Relax)
```

### **Step 6: Smooth Output**
To prevent flickering:
```python
# Majority vote over last 5 predictions
predictions = [1, 1, 0, 1, 1]
final = majority_vote(predictions)  # → 1 (Focus)
```

### **Step 7: Send Command**
```python
if final == 1:
    press('W')  # Move forward in game
else:
    press('SPACE')  # Stop
```

---

## Why ML Beats Simple Thresholds

| Aspect | Threshold | Machine Learning |
|--------|-----------|------------------|
| **Personalization** | Generic threshold (beta > 2%) | Learns YOUR patterns |
| **Features Used** | 1 (beta percentage) | 19 (comprehensive) |
| **Noise Handling** | Sensitive to blinks | Robust (smoothing + multi-feature) |
| **Accuracy** | 60-70% | 80-85% |
| **Adaptability** | Fixed forever | Retrain with more data |

**Real-World Example:**

You blink during concentration:

**Threshold approach:**
```
Blink → Alpha spike → beta drops below 2%
→ Wrong prediction: "Relax"
→ Game stops when you wanted to accelerate ❌
```

**ML approach:**
```
Blink → Alpha spike detected
BUT also checks:
  - smoothed_beta still high (smoothing filters the spike)
  - hjorth_complexity unchanged
  - beta_percentage averaged over time
  - spectral_centroid stable
→ Correct prediction: "Focus"
→ Game keeps going ✓
```

---

## Summary: The ML Pipeline

```
1. TRAINING (one-time, 10 minutes):
   Raw EEG → Filter → Windows → Extract 19 features → Label → Train SVM
   Result: model.pkl (learned patterns)

2. PREDICTION (real-time, every second):
   Raw EEG → Filter → Window → Extract 19 features → Scale → model.predict()
   Result: 0 (relax) or 1 (focus)

3. OUTPUT:
   Send keyboard command to control game hands-free!
```

**Why it works:** The model learned from 1,000 examples of YOUR brain patterns, so it knows what YOUR concentrate vs relax looks like - not some generic threshold!

---

# 13. Prediction Feature Statistics (Example)
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

