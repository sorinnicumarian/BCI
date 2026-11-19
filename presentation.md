# BCI Mouse Control — Presentation Script

---

## Slide 1 — Intro

**Brain-Computer Interface for Hands-Free Mouse Control**
*Controlling a cursor using only brain signals — no hands required*

**Bullets:**
- Single-channel EEG + EOG sensor
- €35 hardware, runs fully offline
- Real-time prediction at 4 Hz

**Speaker notes:**
"Today I'm going to show you a brain-computer interface I built from scratch that lets you control a mouse cursor using only your brain activity and eye movements. No hands, no voice, no external tracking cameras — just three electrodes on your head and a €35 circuit board."

---

## Slide 2 — Motivation

**Who is this for?**

**Bullets:**
- Tetraparesis: paralysis of all four limbs, ~500,000 people in Europe
- Cannot use a keyboard, mouse, touchscreen, or stylus
- A computer cursor is a gateway to communication, work, independence
- Current assistive tech: expensive, fragile, or too limited

**Speaker notes:**
"Tetraparesis means complete loss of motor function in all four limbs — caused by spinal cord injury, ALS, or stroke. For these patients, moving a mouse cursor is impossible. A cursor is not a luxury — it's access to email, video calls, writing, controlling smart home devices. The assistive technology that exists today either costs thousands of euros or has very limited control — sip-and-puff switches give you one bit of information. We can do better."

---

## Slide 3 — Existing Solutions

*(You already have Neuralink and Emotiv here)*

**Add to speaker notes after your slides:**
"Both of these are impressive but they have barriers. Neuralink requires brain surgery. Emotiv requires a full headset and cloud processing. My goal was to explore what's possible at the other extreme — the absolute minimum viable hardware."

---

## Slide 4 — What is a BCI?

**Brain-Computer Interface — how it works**

**Bullets:**
- Neurons fire electrical signals → sum up as tiny voltages on the scalp (microvolts)
- Electrodes on skin pick up these voltages via EEG (Electroencephalography)
- Different mental states produce different frequency patterns in the signal
- A computer reads those patterns and translates them into commands

**Diagram (draw on slide):**
```
Brain activity → scalp voltage → amplifier → ADC → FFT → classifier → mouse
  (neurons)       (microvolts)   (BioAmp)   (Arduino)  (Python)
```

**Speaker notes:**
"A BCI works by listening to the electrical noise your brain produces. Every time a group of neurons fires, it creates a tiny electric field. These fields sum together and can be measured on the scalp — we're talking about signals in the range of 10 to 100 microvolts, about a thousand times smaller than an AA battery. Different mental states leave fingerprints in this signal. Relaxed people produce strong alpha waves at 8–13 Hz. Focused, concentrating people show more beta activity at 13–30 Hz. That difference is what we exploit."

---

## Slide 5 — My Solution

**A €35 single-channel BCI**

**Bullets:**
- **Hardware:** Arduino UNO R4 + BioAmp EXG Pill + 3 gel electrodes
- **Placement:** forehead (signal), mastoid bone behind ear (reference)
- **Sampling:** 512 Hz over USB serial — no Bluetooth, no drivers, no cloud
- **Software:** Python, runs fully offline on any laptop

**Hardware diagram (draw on slide):**
```
[Electrode on forehead] ──┐
                          ├──► BioAmp EXG Pill ──► Arduino UNO R4 ──► USB ──► Laptop
[Electrode on mastoid]  ──┘
```

**Speaker notes:**
"My entire hardware stack costs 35 euros. The BioAmp EXG Pill is an open-source analog front-end — it amplifies the microvolt brain signal up to a readable voltage range and filters out mains noise. The Arduino digitises it at 512 samples per second and sends raw integers over USB to the laptop. Everything else is software. No proprietary drivers, no subscription, no internet."

---

## Slide 6 — EEG Measurement

**From raw signal to brain state**

**Bullets:**
- Raw signal: integer 0–1023 from the Arduino ADC, updating 512× per second
- 1-second sliding window → FFT → power in each frequency band
- **δ delta (0.5–4 Hz):** deep sleep, movement artifacts
- **θ theta (4–8 Hz):** drowsiness, memory
- **α alpha (8–13 Hz):** relaxed, eyes closed
- **β beta (13–30 Hz):** active thinking, concentration, focus
- Band powers are normalised → percentage of total brainwave power

**Signal pipeline — what each step does:**
```
Step 1 — Collect 512 raw samples (1 second)
  Arduino reads pin A0 at 512 Hz, sends integers 0–1023 over USB.
  We wait until we have exactly 512 samples = 1 full second of data.
  Why 1 second? Gives 1 Hz frequency resolution — enough to separate EEG bands cleanly.

Step 2 — Detrend (remove slow drift)
  Fit a straight line through the 512 samples, then subtract it.
  Why? Electrode movement, sweat, and breathing create a slow wandering baseline.
  That drift shows up in the FFT as massive low-frequency energy that swamps real signal.
  Detrending levels the baseline before frequency analysis.

Step 3 — Hann window (reduce spectral leakage)
  Multiply each sample by a bell curve: 0 at the edges, 1 in the middle.
  Why? FFT assumes the block repeats forever. If sample 512 ≠ sample 1,
  there is a sudden jump at the boundary → phantom frequencies bleed everywhere.
  The Hann window fades both ends to zero so there is no discontinuity.

Step 4 — FFT (Fast Fourier Transform)
  Converts the 512 time-domain numbers into 257 frequency-domain numbers.
  Each output bin answers: "how much energy is at X Hz?"
  Bin 1 = 1 Hz, bin 13 = 13 Hz, bin 30 = 30 Hz, up to bin 256 = 256 Hz.
  We square the magnitude of each bin to get power.

Step 5 — Sum power in each band
  Add up all bins that fall inside each named frequency range:
    δ delta   0.5– 4 Hz  → deep sleep, movement artifacts
    θ theta   4– 8 Hz  → drowsiness
    α alpha   8–13 Hz  → relaxed, eyes closed
    β beta   13–30 Hz  → active thinking, concentration
  Result: 4 raw power numbers, one per band.

Step 6 — Normalise to percentages
  Divide each band by the θ+α+β total (δ excluded — drift dominates it).
  Each band becomes a % of the useful frequency content.
  Why? Raw amplitude changes with electrode contact quality; percentages are
  stable across sessions, electrode placement, and different people.

Step 7 — Apply rule (4× per second)
  β% < 13  →  Relax  →  cursor UP
  β% ≥ 13  →  Focus  →  cursor DOWN
  Threshold chosen from calibration recordings.
  Runs every 128 new samples (250 ms) using a sliding window.
```

**Speaker notes:**
"Let me walk through each step. We start by buffering one second of data — 512 samples at 512 Hz. That gives us 1 Hz frequency resolution, enough to separate the EEG bands cleanly.

Before the FFT we detrend. EEG electrodes drift slowly due to sweat, movement, and skin potentials. I fit a straight line through the 512 samples and subtract it. If you skip this, the FFT assigns enormous energy to the lowest frequencies, which contaminates every band.

Then the Hann window. The FFT mathematically assumes our block repeats forever. Our block starts and ends abruptly — the FFT sees that as a sharp edge and creates phantom frequencies across the whole spectrum. The Hann window fades both ends smoothly to zero, eliminating that artefact.

The FFT gives us one power value per frequency bin. We sum the bins inside each named band — four numbers. Then we normalise: express each band as a fraction of the theta+alpha+beta total. This makes the system electrode-contact-independent — a bad connection makes all bands louder equally, but the percentages stay stable. Beta percentage is what the threshold rule operates on."

---

## Slide 7 — Model

**Two approaches: linear rule and ML**

**Binary demo (today):**
- β% < threshold → **Relax** → mouse UP
- β% ≥ threshold → **Focus** → mouse DOWN
- No training required, no model file

**Full 4-class ML — 25 features per window:**
- **Spectral (12):** δ/θ/α/β powers, 5 ratios (α/β, θ/α, β/θ, engagement index), peak frequency, spectral centroid, spectral slope
- **Temporal (8):** Hjorth mobility + complexity, zero-crossing rate, variance, skewness, kurtosis, peak-to-peak, line length
- **Smoothed (3):** exponential moving averages of α and β — reduces window-to-window jitter
- **EOG/DC (2):** window mean (raw eye position), absolute window mean

**Why SVM and not a neural network:**
- ~1,000 labelled windows total → CNN would overfit immediately
- RBF kernel handles non-linear boundaries in feature space
- Inference < 1 ms · beat Random Forest, Gradient Boosting, Ensemble on 5-fold F1

**The cascade (4-class architecture):**
```
β% < 13%               → RelaxUp    (linear rule, no ML)
β% ≥ 13%, α > 0.13     → FocusDown  (linear rule, no ML)
else                   → SVM binary: CBRight vs SingLeft
```
Linear rules handle easy states; SVM only solves the hard 2-class EOG problem.

**Speaker notes:**
"I extract 25 features from each one-second window. Twelve are spectral — the classic EEG bands and their ratios. Eight are time-domain: Hjorth parameters measure how quickly the signal's frequency content changes. Line length — the sum of all sample-to-sample differences — is a powerful detector of saccadic eye movements, which create sharp transients in the signal. Three smoothed features apply an exponential moving average to reduce jitter across windows. And two DC features capture slow eye position that survives the high-pass filter.

I chose SVM because of dataset size. Nine sessions, ~1,000 labelled windows — a convolutional network would overfit immediately. SVM with RBF kernel is the standard for single-channel BCI with limited data, and it beat every alternative on cross-validated F1.

The cascade splits the problem: linear thresholds handle relax and focus, which differ clearly in beta power. The SVM only ever faces a 2-class choice between the two eye-movement states — smaller decision space, better accuracy."

---

## Slide 8 — Results

**Bullets:**
- Binary relax/focus: live demo — works in real time
- 4-class accuracy (SVM, dataset 06): **~65%** — chance level 25%
- 4-class accuracy (SVM, dataset 09, glance paradigm): **75.5%**
- 5-fold cross-validation F1 score: **0.57**
- Latency: ~1.25 seconds (1s window + buffer)
- Prediction rate: 4 Hz

**Speaker notes:**
"On a 4-class problem — up, down, left, right — chance is 25%. The trained SVM reaches 75% accuracy on the best dataset. That's not good enough for a commercial product but it demonstrates that the signal genuinely contains discriminative information. The binary demo is more robust because it's a simpler decision boundary. One honest limitation: accuracy varies significantly with electrode placement, skin impedance, and the subject's ability to maintain a consistent mental state."

---

## Slide 9 — Demo

**What you'll see:**
- Three electrodes, one USB cable
- Terminal streaming band powers live at 4 Hz
- Mouse cursor moving up (relax) and down (focus)

**To run:**
```bash
cd python_solution && ./predict.py
```

**Cues:**
- Relax, breathe slowly, stare at a fixed point → β drops → cursor UP
- Count backwards from 300 in steps of 7 → β rises → cursor DOWN

**Speaker notes:**
"Let me put the electrodes on now. You'll see the terminal printing delta, theta, alpha, and beta percentages four times per second. The cursor will start moving when the beta threshold is crossed. I'll relax first — you should see the cursor drift upward. Then I'll concentrate hard — count backwards — and the cursor should come down."

---

## Slide 10 — Future Steps

**Bullets:**
- **Better electrode placement** — outer eye corner for eye-movement (EOG) based left/right control
- **Stable 4-class ML** — replace linear cascade with a single trained classifier across all 4 directions
- **Double-blink = click** — blink detection pipeline already implemented
- **Miniaturise** — Raspberry Pi Zero W + LiPo battery → fully wearable, no laptop needed
- **Clinical testing** — validate with tetraparesis patients in a rehabilitation setting

**Speaker notes:**
"The next step is electrode stability. The outer eye corner gives a much stronger signal for horizontal eye movements but the adhesive keeps slipping. Once that's solved, I can collect clean labelled data and train a proper 4-class model. Longer term, the goal is a self-contained device — nothing bigger than a pair of glasses — that a patient with no motor function can put on themselves and use independently. The hardware cost at that scale is under 50 euros."

---

## Slide 11 — Q&A Prep (your notes, not shown to audience)

**Numbers to have ready:**
- €35 hardware · 512 Hz · single channel · 75.5% accuracy · 4 Hz · ~1.25 s latency

---

**"Is 75% accurate enough for real use?"**
Accuracy alone is the wrong metric — Information Transfer Rate matters more.
At 4 Hz with 75%, you get ~3 correct decisions/second.
For continuous cursor movement errors are recoverable — the cursor just drifts back.
Commercial 14-channel headsets reach 85–90%. Single channel at 75% is a strong baseline.

**"Why 75% on binary but only 65% on 4-class?"**
Binary is inherently easier — two clearly different tasks.
4-class adds relax and focus which overlap in feature space.
The cascade partially solves this by splitting it into easier sub-problems.

**"Does it work for everyone? Does it need retraining per person?"**
Yes, per-person calibration is required (~4 min session).
EEG baselines are highly individual — band power levels vary between people.
Session-to-session transfer without retraining is an open research problem in BCI.

**"Why single channel — why not more electrodes?"**
Target users cannot place electrodes themselves.
Single channel + correct placement beats 14 channels placed badly.
More channels is a future step once the placement methodology is proven.

**"Why not use EMG instead? Muscle signals are much stronger."**
EMG requires intentional muscle contractions.
Tetraparesis patients may have zero voluntary motor control below the neck.
EEG and EOG are passive — no movement required.

**"What about signal quality day to day?"**
Electrode impedance and skin preparation vary. This is a known limitation.
Adaptive classifiers that update during use exist in research but not implemented here.
Calibration at session start (collect 4 min of labelled data) partially addresses it.

**"What's the latency? Can it be reduced?"**
~1.25 s — 1 s window + buffer fill time.
Could go to 0.5 s with a smaller window but frequency resolution degrades.
For slow cursor control, 1.25 s is acceptable.

**"Why not use MNE or OpenBCI libraries?"**
Those assume multi-channel headsets with dedicated USB dongles.
Arduino-over-serial is non-standard.
Building from scratch also forced understanding every artifact directly — essential for debugging.

**"Is it safe?"**
BioAmp EXG Pill operates at 3.3V and only reads voltage — no current applied to user.
Passive sensing device, galvanically isolated from mains power.

---

## Slide 12 — Questions

*(open floor)*
