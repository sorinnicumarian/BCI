
# Brain–Computer Interface (BCI) – 4-Class EEG+EOG Mouse Control

## Quick Start
```bash
cd python_solution
./collect.py <state_name> [seconds]   # collect data
./predict.py                          # run live prediction
```

---

## Table of Contents
1. [Project Goal](#1-project-goal)
2. [Hardware Setup](#2-hardware-setup)
3. [Electrode Placement History](#3-electrode-placement-history)
4. [4-Class System Architecture](#4-4-class-system-architecture)
5. [Dataset History & Accuracy](#5-dataset-history--accuracy)
6. [Scripts Reference](#6-scripts-reference)
7. [Signal Quality Guide](#7-signal-quality-guide)
8. [EEG/EOG Background](#8-eegeog-background)
9. [Machine Learning Approach](#9-machine-learning-approach)
10. [License](#10-license)

---

# 1. Project Goal

Mouse control for **tetraparesis patients** (4-limb paralysis) using a single EEG/EOG channel.

Four mental states → four mouse directions:

| State | Mental Task | Eye Movement | Mouse |
|-------|------------|--------------|-------|
| **RelaxUp** | Relax / blank mind | Look up (sustained) | ↑ Up |
| **FocusDown** | Count backwards | Look down (sustained) | ↓ Down |
| **CBRight** | Count backwards | Glance right repeatedly | → Right |
| **SingLeft** | Sing mentally | Glance left repeatedly | ← Left |

**Double blink → Left Click**

---

# 2. Hardware Setup

- **Arduino UNO R4** — samples at 512 Hz, streams raw ADC via USB serial
- **BioAmp EXG Pill** — single-channel differential amplifier
- **Sketch:** `arduino_solution/signal.ino` — raw ADC output, no onboard filters

**Wiring:**
```
BioAmp EXG Pill → Arduino UNO R4
  VCC → 5V
  GND → GND
  OUT → A0
```

**Expected signal:** ADC values around 512 (midpoint of 0–1023 range), varying ±10–50 counts with EEG/EOG.

---

# 3. Electrode Placement History

## 3.1 Wire color convention (BioAmp EXG Pill)
- **Red** → IN+ (positive differential input)
- **Black** → IN− (negative differential input)
- **Yellow** → REF (bias / reference, helps common-mode rejection)

## 3.2 Placement attempts (chronological)

### Placement A — Original (Datasets 01–07)
| Wire | Location |
|------|----------|
| Red (IN+) | Forehead center |
| Black (IN−) | Left mastoid (behind left ear) |
| Yellow (REF) | Right mastoid (behind right ear) |

**Result:** Excellent signal stability. Good RelaxUp/FocusDown detection (alpha/beta). No horizontal eye movement (HEOG) capture — left/right was brain-state only.

---

### Placement B — Outer Canthus (Dataset 08) ✓ BEST ACCURACY
| Wire | Location |
|------|----------|
| Red (IN+) | Forehead center |
| Black (IN−) | Left outer canthus (corner of left eye) |
| Yellow (REF) | Right mastoid |

**Result:**
- Confirmed ~480 ADC looking left, ~520 ADC looking right (40 count HEOG signal)
- Binary (CBRight vs SingLeft) accuracy: **84%**
- 4-class accuracy: **62%**
- **Issue:** Snap connector on black wire was unreliable — electrode kept losing contact. The outer canthus is a curved, bony surface — electrode pad adhesion alone is not enough. The snap connector must be fully seated and taped over.

**Why this placement works:** The forehead–outer-canthus axis captures both vertical EOG (VEOG, from forehead height) and horizontal EOG (HEOG, from lateral eye position). Lateral gaze creates a ±47 ADC transient per saccade (eye movement gesture).

---

### Placement C — Temple (attempted, abandoned)
| Wire | Location |
|------|----------|
| Red (IN+) | Forehead center |
| Black (IN−) | Left temple (temporal region) |
| Yellow (REF) | Right mastoid |

**Result:** Failed. The temporalis muscle overlies the temple — any jaw movement, swallow, or facial expression creates massive EMG artifacts (100–300 ADC spikes) that exceed the artifact rejection threshold. Signal cannot be maintained.

---

### Placement D — Swapped polarity (mistake, fixed)
At one point red and black were accidentally swapped:
- Red on outer canthus (IN+), Black on forehead (IN−)
- Result: `raw=1023` (ADC saturated at VCC) — skin DC offset between those locations rails the amplifier
- Fix: always keep Red on forehead

---

## 3.3 Recommendation for outer canthus use
To make Placement B reliable:
- Use **pre-gelled disposable ECG electrode pads** (e.g. 3M Red Dot) — the BioAmp snap connector fits directly
- After snapping on, place a strip of **micropore medical tape** over the snap+electrode to mechanically lock the connection
- Clean skin with alcohol wipe before placing
- Wait 30–60 seconds after placement for the skin-electrode interface to stabilize

---

# 4. 4-Class System Architecture

## Hybrid cascade (predict.py)

```
Raw ADC (512 Hz)
       │
       ├─── Per-sample IIR pipeline ──→ EOG envelope ──→ Blink detection
       │                                                    (double blink = left click)
       │
       └─── 512-sample rolling window (every 256 samples = 0.5s)
                    │
                    ├─ Artifact rejection:
                    │    • std < 1e-3 → flat/dead electrode
                    │    • ADC > 1000 or < 20 → saturation
                    │    • >50% samples with z > 4 → persistent noise
                    │
                    ├─ Scipy filters: notch(50Hz) → bandpass(0.5–30Hz)
                    │
                    ├─ 25 features extracted
                    │
                    └─ Hybrid cascade:
                         beta% < 13%  → RelaxUp   (linear rule)
                         alpha > 13%  → FocusDown  (linear rule)
                         else         → ML (SVM binary: CBRight vs SingLeft)
```

## Why hybrid?
- RelaxUp and FocusDown are dominated by **brain state** (alpha/beta power) — linear rules are fast and interpretable
- CBRight and SingLeft require **EOG + mental task combination** — ML handles this

## Majority vote
Last 3 predictions are majority-voted before sending mouse command, smoothing out single bad windows.

---

# 5. Dataset History & Accuracy

## 5.1 Full dataset log

### Datasets 01–03 — 2-Class (Concentrate vs Relax)
**Electrode:** Red=forehead center, Black=left mastoid, Yellow=right mastoid
**Goal:** Original game control (car game) — focus=accelerate, relax=brake
**Paradigm:** Sustained concentration (games, mental math) vs eyes-closed meditation
**Duration:** ~5 min/class each session
**Samples:** ~150k rows (~5 min at 512 Hz) per file
**Accuracy:** 77–80% (SVM, 2-class)
**Notes:** Clean stable signal. Strong alpha/beta separation. Foundation for all later work.

---

### Dataset 04 — 4-Class Attempt with Motor Imagery
**Electrode:** Red=forehead center, Black=left mastoid, Yellow=right mastoid (unchanged)
**Goal:** Add left/right fist clenching as two new classes
**Classes:** relax, concentrate, left_fist_clench, right_fist_clench
**Duration:** ~30s/class
**Samples:** ~15k rows/class
**Accuracy:** ~65% (4-class)
**Notes:** Motor imagery with single forehead electrode doesn't capture enough signal. Abandoned. Left/right fist clenching is not distinguishable from this placement.

---

### Dataset 06 — First 4-Class Eye+Mental (with "pulse" movements)
**Electrode:** Red=forehead center, Black=left mastoid, Yellow=right mastoid
**Goal:** First attempt at 4-class eye movement + mental state control
**Classes:** relax_pulse_up, focus_pulse_down, count_backwards_pulse_right, sing_pulse_left
**Paradigm:** "Pulse" = brief repeated eye movements (not sustained gaze)
**Duration:** ~2 min/class (~62k rows)
**Accuracy:** 68.5% (4-class SVM)
**Notes:** "Pulse" in filenames = blinking-style eye movements. Forehead+mastoid axis captures vertical EOG (up/down) reasonably. No HEOG on this axis — left/right relies entirely on mental task difference.

---

### Dataset 07 — Binary CBRight vs SingLeft (additional data)
**Electrode:** Red=forehead center, Black=left mastoid, Yellow=right mastoid (unchanged)
**Goal:** Collect more left/right data to improve binary model
**Classes:** count_backwards_right, sing_left (binary only)
**Duration:** ~2 min/class (~62k rows)
**Accuracy:** 64.9% (binary SVM, datasets 06+07 combined: 74.6% ensemble)
**Notes:** Combined with dataset 06 + 4 new features (skewness, kurtosis, peak_to_peak, line_length) + window_mean improved to 74.6%.

---

### Dataset 08 — Outer Canthus Placement ✓ Best result
**Electrode:** Red=forehead center, Black=**left outer canthus** (corner of eye), Yellow=right mastoid
**Goal:** Capture horizontal EOG (HEOG) for better left/right separation
**Classes:** relax_up, focus_down, count_backwards_right, sing_left
**Paradigm:** Sustained gaze in each direction + mental task
**Duration:** ~30s/class (~16k rows)
**Accuracy:** **84% binary (CBRight vs SingLeft)**, 62% 4-class
**Signal:** Confirmed ~480 ADC looking left, ~520 ADC looking right (40 count HEOG differential)
**Notes:** First dataset with confirmed HEOG signal. The saccade at the start of each recording (transition moment) created a ±47 ADC spike visible in the raw signal. Sustained gaze DC offset was only ~0.6 ADC (filtfilt normalizes it over 30s). Model primarily used mental task features (smoothed_alpha, smoothed_ratio) + saccade transient. Electrode contact was unstable — snap connector at outer canthus kept losing contact.

---

### Dataset 09 — Glance Gesture Paradigm
**Electrode:** Red=forehead center, Black=**left outer canthus** (corner of eye), Yellow=right mastoid
**Goal:** Replace sustained gaze with deliberate glance gestures for cleaner saccade signal
**Classes:** relax_up, focus_down, count_backwards_right, sing_left
**Paradigm:**
- Left/Right: **glance left/right then return to center, repeat** — each glance = ±47 ADC saccade
- Up/Down: **sustained gaze** + mental state (relax or count)
**Duration:** ~60s/class (~31k rows)
**Accuracy:** 75.5% binary (CBRight vs SingLeft), 60.2% 4-class
**Signal:** line_length for glance states (796–885) vs sustained (513–526) confirmed saccades captured
**Notes:** Glancing clearly captured in line_length and peak_to_peak features. window_mean diff only 2.4 ADC (weak direction signal). Electrode connector remained unreliable — lost signal repeatedly during live prediction due to snap connector issue at outer canthus and temporal muscle EMG interference when placed at temple instead.

---

## 5.2 Feature set (25 features, datasets 06 onward)
Spectral: `E_alpha, E_beta, E_theta, E_delta, alpha_beta_ratio, theta_alpha_ratio, beta_theta_ratio, engagement_index, beta_percentage, peak_frequency, spectral_centroid, spectral_slope`

Temporal: `hjorth_mobility, hjorth_complexity, zero_crossing_rate, signal_variance, signal_skewness, signal_kurtosis, peak_to_peak, line_length`

Smoothed: `smoothed_beta, smoothed_alpha, smoothed_ratio`

EOG/DC: `window_mean, window_mean_abs` (computed on notch-only signal, before HPF destroys DC component)

## 5.3 Key insights
- **Sustained gaze DC offset** is destroyed by the 0.5 Hz HPF over a 30s window → use notch-only signal for window_mean
- **Saccade transients** (eye movement gestures) ARE captured: ±47 ADC spike, visible in line_length and peak_to_peak
- **Mental task** (counting vs singing) is the primary discriminator for left/right — alpha/beta differences are real
- **Forehead+mastoid** vertical axis captures VEOG (up/down) but no HEOG
- **Forehead+outer canthus** diagonal axis captures both — but electrode contact is the limiting factor

### Feature set (25 features, all datasets from 06+)
Spectral: `E_alpha, E_beta, E_theta, E_delta, alpha_beta_ratio, theta_alpha_ratio, beta_theta_ratio, engagement_index, beta_percentage, peak_frequency, spectral_centroid, spectral_slope`

Temporal: `hjorth_mobility, hjorth_complexity, zero_crossing_rate, signal_variance, signal_skewness, signal_kurtosis, peak_to_peak, line_length`

Smoothed: `smoothed_beta, smoothed_alpha, smoothed_ratio`

EOG/DC: `window_mean, window_mean_abs` (computed on notch-only signal, before HPF destroys DC component)

### Key insight: glance vs sustained EOG
- **Sustained gaze** (looking left/right continuously): The HPF in the bandpass filter destroys the DC component over a 30s window. `window_mean` barely differs between left/right (0.6 ADC).
- **Glance gesture** (flick left/right then return to center): Each saccade creates a ±47 ADC transient visible in `line_length` and `peak_to_peak`. `window_mean` captures a partial shift (~2.4 ADC/glance).
- Model discriminates using **both EOG transients AND mental task** (alpha/beta patterns from counting vs singing).

---

# 6. Scripts Reference

## collect.py
Collects raw EEG/EOG data from Arduino and saves to CSV.

```bash
./collect.py <state_name> [seconds]
# e.g.: ./collect.py 10_relax_up 60
# Saves to: ../artefacts/data/<state_name>.csv
```

- Progress bar with countdown
- Press Enter to stop early
- Plays Glass.aiff sound on completion
- Warns if fewer than 90% of expected samples collected
- Auto-detects Arduino port (excludes Bluetooth/debug-console)

## predict.py
Live 4-class prediction with mouse control.

```bash
./predict.py
# or: BCI_PORT=/dev/cu.usbmodem2101 ./predict.py
```

**Display legend:**
```
β%     = beta band power %       (low β → RelaxUp linear rule)
α%     = alpha band power %      (high α → FocusDown linear rule)
δ%     = delta band power %      (high δ = movement/noise/poor contact)
θ%     = theta band power %
w_mean = raw DC level            (eye position: ~480 left, ~520 right)
pCB    = ML prob → CBRight       (only shown when linear rules don't fire)
pSL    = ML prob → SingLeft      (only shown when linear rules don't fire)
method = what triggered decision: linear rule or ML
votes  = last 3 predictions      (majority wins)
```

**Signal quality indicators:**
- `⏳ Waiting for first valid window... raw=NNN` — normal startup
- Normal output — good contact, predictions running
- `⚠ SIGNAL LOST (Ns) — check electrode raw=NNN` — electrode lost contact

**Cascade thresholds (tune if needed):**
```python
BETA_RELAX_THRESH  = 13.0   # beta% below this → RelaxUp
ALPHA_FOCUS_THRESH = 0.13   # alpha above this (and beta > thresh) → FocusDown
```

## detect.py
Calibration tool — measures personal brainwave values and suggests threshold adjustments.

```bash
./detect.py relax focus
```

## notebook/create_prediction_model.ipynb
Training notebook. Cells are numbered by dataset. Run the last two cells for the latest model.

Current active cells:
- `dja2atoz16j` — load dataset 09, extract features, check HEOG signal
- `v1drh1b3xze` — train SVM/RF/GB/Ensemble, save model.pkl + scaler.pkl

---

# 7. Signal Quality Guide

## Good signal
```
β=8.2%  α=12.4%  δ=55.3%  θ=8.1%  w_mean=513.2  | method=linear β<13.0  | votes=[000] → RelaxUp
```
- `δ` ideally below 70% (some delta is normal, high delta = movement/noise)
- `w_mean` should be 490–530 (near 512 midpoint)
- Output changes every second (not frozen)

## Electrode lost contact
```
⚠  SIGNAL LOST (8s) — check electrode  raw=634
```
- `raw` values jumping wildly (300–700 range) = floating input
- `raw=1023` constantly = ADC saturated (polarity wrong or electrode rail)
- `raw` frozen at same value = flat signal (full disconnection)

## Artifact rejection thresholds
| Check | Condition | Meaning |
|-------|-----------|---------|
| `std < 1e-3` | Flat signal | Dead electrode |
| `x.max() > 1000` | Near rail high | Saturation |
| `x.min() < 20` | Near rail low | Saturation |
| `>50% samples z > 4` | Persistent noise | Floating or muscle EMG |

## Interpreting δ%
- δ < 50%: clean signal
- δ 50–80%: some noise/movement, model still works
- δ > 90%: heavy noise — electrode contact poor or large movement artifacts

---

# 8. EEG/EOG Background

## EEG Frequency Bands
| Band | Hz | Mental state |
|------|----|--------------|
| Delta | 0.5–3 | Sleep, heavy artifacts |
| Theta | 4–7 | Drowsy, daydreaming |
| Alpha | 8–13 | Relaxed, eyes closed/up |
| Beta | 13–30 | Focus, concentration, counting |

## EOG (Electrooculography)
Eye movement generates a dipole potential (~1mV). The cornea is positive, retina is negative.

- **Looking right** → corneal positive pole moves right → voltage rises on right, falls on left
- **Looking left** → opposite
- **Blink** → vertical EOG spike (100–300µV) → detected in the blink pipeline

With forehead (IN+) to outer canthus (IN−):
- Right gaze: forehead voltage unchanged, outer canthus voltage shifts → net differential changes
- Measured: ~47 ADC per full lateral gaze (dataset 08 confirmation)

## Why the 0.5Hz HPF destroys sustained EOG
The bandpass filter (0.5 Hz HPF) uses `filtfilt` (zero-phase, applied forward+backward). Over a 30s recording of sustained left gaze, the filter normalizes away the DC offset. Fix: compute `window_mean` on the **notch-only** signal before applying HPF.

---

# 9. Machine Learning Approach

## Pipeline
```
Raw EEG (512 Hz)
→ Notch filter (50 Hz, Q=30)        # remove mains interference
→ Bandpass filter (0.5–30 Hz)       # remove DC drift + high-freq noise
→ 25 features per 512-sample window
→ StandardScaler normalization
→ Binary SVM (CBRight vs SingLeft)
```

## Feature importance (Random Forest, dataset 09)
Top features for left/right discrimination:
1. `smoothed_alpha` — mental state (singing vs counting)
2. `window_mean` — DC eye position component
3. `line_length` — total signal variation (glance = high)
4. `window_mean_abs` — magnitude of DC shift
5. `spectral_slope` — frequency distribution

## Model selection
GridSearchCV over SVM + RandomForest + GradientBoosting. Best by 5-fold F1 is saved.
Current best: SVM (dataset 09), 75.5% binary accuracy.

---

# 10. License
MIT License
