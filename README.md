# Collect
00
01
 - concentrate
 - relax
02
 - concentrate
 - relax 
03
 - black on left
 - yellow on right
 - subway surfer

# Setup
# Abbreviatons
1. FFT = Fast Fourier Transform.
It simply answers the question:

“Instead of showing me the signal in time, show me how much of each frequency it contains.”

Imagine hearing a music chord (many notes mixed).
FFT tells you which musical notes are inside.
For EEG:

Alpha waves = 8–13 Hz
Beta waves = 13–30 Hz

FFT tells us “how strong” each of these waves are.

2. PSD = Power Spectral Density.
FFT tells us what frequencies exist.
PSD tells us how strong each frequency is.
High‑school analogy:

FFT shows each note in a song.
PSD shows how loud each note is.

For EEG, PSD tells us things like:

“Is alpha strong?” → relaxed
“Is beta strong?” → focused
“Is theta strong?” → sleepy

# Context
0. Brain-Computer Interface (BCI) system that leverages electroencephalography (EEG) signals to control external devices in real-time. This project demonstrates how EEG signals can be classified into different mental states (attentive and relaxed) to control a car racing game without physical input devices. 

1. Base value = 512. If a value = 519, consider it a note from a song. It does not say if a song is energetic or slow. You need to know how fast the notes are played in order to figure out if it a DnB song or not. 

So, the concentration is given by how fast the values rise or fall.
Concentration = faster wiggles (13–30 Hz → Beta waves).
Relaxation = slower wiggles (8–13 Hz → Alpha waves). That’s 8–13 cycles per second → relaxation.

if the signal is basically flat (not wiggling fast OR slow), you are doing nothing special: just awake, neutral.
But this rarely happens because EEG is never perfectly still.

 [![Watch the video]https://youtube.com/shorts/p9bGwBhwvZo?si=rk1a1hAxnOOrg34C

2. Band Hz - What it means (simple)Delta0.5–3deep sleep / slow wavesTheta3–8daydreaming / tiredAlpha8–13relaxed but awakeBeta13–30focused / thinking hard
We don’t bother with Gamma because cheap sensors can’t measure it well.

3. Why compute things like alpha/beta ratio?
Because they are easy mental‑state indicators:

When you relax, alpha ↑
When you focus, beta ↑

So:
alpha_beta_ratio=alpha powerbeta power\text{alpha\_beta\_ratio} = \frac{\text{alpha power}}{\text{beta power}}alpha_beta_ratio=beta poweralpha power​
If this ratio is:

HIGH → you are relaxed
LOW → you are focused

This is why we use it to move a car forward or stop in a BCI game.

3. SVM = Support Vector Machine, a type of machine‑learning classifier.
But high‑school version:

It finds the best line that separates two groups of points.

Imagine plotting:

alpha power on x‑axis
beta power on y‑axis

Relaxed points cluster in one area,
Focused points cluster in another area.
SVM draws the line between them

4. Full car game PoC flow 
Arduino reads EEG voltage
Arduino filters it (0.5–30 Hz)
Python receives samples
Python computes PSD
Python calculates alpha & beta
Python sends features to the SVM model
Model decides:

focus → send “move forward”
relaxed → send “stop”


Arduino receives command
Game responds

## Arduino Hardware Installation Steps
1. Connect your Arduino board to the PC via a USB cable.
2. Connect the BioAmp EXG Pill to the EEG sensors
3. Connect the BioAmp EXG Pill to the Arduino Board in this way: 
 - VCC to 5V
 - GND to GND
 - OUT to A0
 According to this image: /artefacts/images/connection_bioamp_exg_pill_to_arduino.png

## Arduino Software Installation Steps
1. Install latest Arduino IDE

## Arduino Software Test Steps
1. Go to arduino_tests folder and test sequentially
1.0 - test arduino board
1.1 - test if the Bio Amp EXG Pill and the EEG sensors read some values
1.2 - test EEG Filter 
 
According to this image /Users/sorin/Documents/Repos/BCI/artefacts/images/arduino_test_02-eeg-filter.png

The goal of this test is to make sure that the Arduino is correctly filtering the raw EEG signal from the BioAmp EXG Pill before the data is used for further processing (FFT, PSD, alpha/beta calculations, machine learning, etc.).
EEG signals are extremely small and easily buried under noise (muscles, eye blinks, electrical interference).
To use EEG for machine‑control (e.g., controlling a game with “focus” vs. “relax”), we must keep only the useful brainwave frequencies and remove everything else.
This test verifies that the band‑pass filter running on the Arduino works as expected.

Keep (pass-band)

0.5–29.5 Hz
This range contains the brain rhythms used for mental‑state recognition:
Delta (0.5–3 Hz)
Theta (3–8 Hz)
Alpha (8–13 Hz)
Beta (13–30 Hz)

Remove (stop-band)

Noise slower than 0.5 Hz (movement, drift)
Noise faster than 30 Hz (muscle activity, EMG, electrical interference)
Most 50/60 Hz mains noise

The BioAmp EXG Pill outputs an amplified EEG signal that is DC‑biased to mid‑supply before entering the Arduino’s ADC.
Since the Arduino ADC converts 0–5V into digital values 0–1023, the midpoint (≈2.5 V) corresponds to ≈512 in ADC units.
Because EEG voltages are extremely small (microvolts), the amplified waveform appears as small variations around the midpoint.
Therefore, filtered EEG samples typically appear in the range ≈450–600, oscillating around ~512.
This behavior is normal and indicates that:

the sensor is connected correctly
the band‑pass filter is working
the ADC is receiving a stable, centered signal
the EEG waveform is present as small deviations around the baseline

A “PASS” is confirmed when the signal shows stable fluctuations around 512, without clipping (0 or 1023) and without drifting out of range.

🧪 5. When this output is considered CORRECT (PASSED)
Your filter test is PASSED when:
✔ The output values stay roughly between 400 and 600
→ Shows the sensor is biased and amplified correctly.
✔ The values fluctuate (not flat)
→ Shows your EEG + noise is being picked up.
✔ The numbers update at 256 samples/sec
→ Shows your sampling loop is accurate.
✔ No values hit 0 or 1023
→ Means no clipping — signal is within safe range.
✔ The average stays near 512
→ Confirms correct biasing of the BioAmp output.
All of your sample readings meet these criteria → Your system is working properly.

1.3 BCI FTT
Samples A0 at SAMPLE_RATE (intended 500/512 Hz).
Filters each sample: 50 Hz notch + 45 Hz low‑pass.
Every FFT_SIZE samples, runs a real‑FFT (CMSIS‑DSP).
Builds a power spectrum and sums power in EEG bands.
Smooths the bandpowers and prints normalized percentages:
delta%,theta%,alpha%,beta%,gamma%

# 
cd BCI
source .venv/bin/activate
python your_script.py

# Prediction
	E_alpha	E_beta	E_theta	E_delta	alpha_beta_ratio	peak_frequency	spectral_centroid	spectral_slope	label
count	1076.000000	1076.000000	1076.000000	1076.000000	1076.000000	1076.000000	1076.000000	1076.000000	1076.000000
mean	5.233325	11.234776	5.386478	9.540712	0.628554	7.361088	11.386523	-10.798197	0.570632
std	4.433682	7.175591	17.610713	15.219221	0.705698	7.718291	3.803338	0.572749	0.495216
min	0.209921	0.508195	0.069137	0.059225	0.033710	0.000000	3.086847	-13.068684	0.000000
25%	2.368279	5.292577	0.912572	1.431014	0.263072	0.998051	8.437347	-11.138286	0.000000
50%	4.116698	10.165796	1.660228	4.291459	0.447632	3.992203	11.687700	-10.710864	1.000000
75%	6.815488	16.141536	2.938309	11.400323	0.758137	12.226121	14.078900	-10.390765	1.000000
max	36.817454	47.571487	244.958174	192.066974	8.958952	29.941520	21.986947	-9.546009	1.000000

Short answer: mostly plausible, but there are 3 red flags you should fix before trusting the model:

peak_frequency has a minimum of 0 Hz → residual DC/very‑low‑frequency energy is leaking in.
spectral_slope ≈ −10.8 ± 0.57 → the scale is off (typical EEG 1/f slopes on log–log are around −1…−2).
Theta/Delta have very large maxima (≈245, 192) → heavy‑tailed outliers (likely motion/eye/muscle artifacts).

Below I explain what looks good, what’s suspicious, and how to fix it quickly.
 What looks reasonable

Class balance: label mean ≈ 0.571 → about 57% class 1 / 43% class 0 (not wildly imbalanced).
Alpha/Beta ratio: mean 0.63, IQR ~0.26–0.76 (reasonable if recordings contain more “focused” segments on average). Max 8.96 means some eyes‑closed/relax chunks with dominant alpha—fine.
Spectral centroid ~11.39 Hz (±3.8) → center of mass near the alpha/theta boundary—plausible for resting/task EEG.
Peak frequency: median ~4 Hz, 75th percentile ~12.23 Hz, max ~29.94 Hz → dominant peaks in theta/alpha/beta bands as expected.

So directionally, the features look like EEG.

⚠️ What’s suspicious (and why)


peak_frequency min = 0 Hz
With a 0.5–30 Hz band‑pass, the PSD peak should not be at 0 Hz. Zero‑Hz peaks usually mean:

DC wasn’t fully removed (filter issue), or
the Welch estimate still sees a maximum at the DC bin because the segment wasn’t centered/properly filtered.



spectral_slope ≈ −10.8
A log–log fit of PSD vs frequency for EEG typically yields slopes around −1 to −2 (1/f^k). Values near −10 suggest:

You’re fitting ln(PSD) vs ln(f) including f=0 (you trimmed f[1:], good—but peak at 0 can distort neighborhood),
or the units/scaling are off (e.g., not restricting the fit to 2–30 Hz),
or PSD magnitudes are tiny and numerical scale dominates.
→ Limit the fit to a clean band (e.g., 2–30 Hz) and use log10 for interpretability.



Huge outliers in theta/delta

E_theta max ≈ 245, E_delta max ≈ 192 with medians ~1.66 and ~4.29 → extremely heavy tails.
Likely artifacts (movement/eye blinks) not rejected; they will swamp bandpowers and confuse the classifier.

## License
This project is licensed under the MIT License.