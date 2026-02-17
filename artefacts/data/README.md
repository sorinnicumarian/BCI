# EEG Training Data

This directory contains EEG signal recordings for training the BCI focus/relax classifier.

## Data Format

All CSV files have two columns:
- `timestamp`: Recording timestamp
- `value`: Raw ADC value from BioAmp EXG Pill (0-1023 range)

Sampling rate: **512 Hz** (Arduino configured with `SAMPLE_RATE 512`)

---

## Datasets

### Dataset 01, 02, 03
- **Status**: Historical data, may not generalize well
- **Note**: Different electrode placement/session conditions
- **Not recommended** for current deployment

---

### Dataset 04 ✓ **CURRENT - RECOMMENDED**

**Collection Date**: February 17, 2025
**Electrode Placement**: [Document your specific placement]
**Hardware**: Arduino UNO R4 + BioAmp EXG Pill

#### 04_relax.csv
- **Duration**: ~2 minutes (489 KB, ~60,000 samples)
- **Mental State**: Complete relaxation
- **Conditions**:
  - Eyes CLOSED
  - Clear mind, no active thoughts
  - Slow breathing
  - No muscle tension

#### 04_concentrate.csv
- **Duration**: ~2 minutes (481 KB, ~60,000 samples)
- **Mental State**: Intense visual focus
- **Conditions**:
  - Eyes OPEN
  - Focused on **car logo** (specific visual target)
  - Imagining the car moving forward
  - Sustained attention for entire duration

**Why Dataset 04 Works:**
- Training and deployment conditions **exactly match**
- Specific focus target (car logo) creates reproducible mental state
- Clear distinction between eyes-closed-relax vs eyes-open-focus
- Same electrode placement for both collection and live use

---

### Dataset 05 ✓ **CURRENT - 4-CLASS MOUSE CONTROL**

**Collection Date**: February 17-18, 2025
**Electrode Placement**: [Document your specific placement]
**Hardware**: Arduino UNO R4 + BioAmp EXG Pill

#### 05_relax.csv
- **Duration**: 5 minutes
- **Mental State**: Pulse relaxation
- **Conditions**:
  - Eyes OPEN
  - Pulse relax state
  - Imagine mouse cursor moving DOWN
  - Relaxed but not sleeping

#### 05_concentrate.csv
- **Duration**: 5 minutes
- **Mental State**: Pulse focus
- **Conditions**:
  - Eyes OPEN
  - Pulse focus/concentration
  - Imagine mouse cursor moving UP
  - Sustained intense focus

#### 05_left_fist_pulse.csv
- **Duration**: 5 minutes
- **Mental State**: Visual focus on football
- **Conditions**:
  - Eyes OPEN
  - Watched **football** (specific visual target)
  - Pulse attention pattern
  - Associated with LEFT cursor movement

#### 05_right_fist_clench.csv
- **Duration**: 5 minutes
- **Mental State**: Visual focus on star
- **Conditions**:
  - Eyes OPEN
  - Watched **star** (specific visual target)
  - Sustained attention
  - Associated with RIGHT cursor movement

**Why Dataset 05 (4-Class) Works:**
- All states with **eyes OPEN** (consistent baseline)
- **Visual targets** instead of motor imagery (more reliable with single channel)
- **Pulse patterns** add temporal variation
- Specific focus objects (football, star) create distinct brain states
- Matches mouse control deployment: UP, DOWN, LEFT, RIGHT

---

## Collection Protocol (for future sessions)

Use `python_solution/collect.py` to record new sessions:

```bash
cd python_solution
./collect.py  # Run for 2-3 minutes
mv signal.csv ../artefacts/data/05_relax.csv  # or 05_concentrate.csv
```

### Best Practices
1. **Keep electrode placement identical** for relax and concentrate sessions
2. **Use the same focus target** during collection and deployment
3. **Minimum 2 minutes per session** (~60,000 samples at 512 Hz)
4. **Take 30-second break** between relax and concentrate recordings
5. **Document your focus target** (what you look at, imagine, etc.)
6. **Maintain consistency** - same environment, same mental approach

### Troubleshooting
- If model doesn't work live → collect new data matching deployment conditions
- If accuracy is low → increase distinction between mental states
- If predictions are biased → check class balance in training data

---

## Model Training

The notebook `notebook/create_prediction_model.ipynb` expects these files:
- Update the cell that loads data to reference your current dataset
- Example for Dataset 04:
  ```python
  df0 = pd.read_csv('../artefacts/data/04_relax.csv')
  df1 = pd.read_csv('../artefacts/data/04_concentrate.csv')
  ```

Training produces:
- `python_solution/model.pkl` - Trained SVM classifier
- `python_solution/scaler.pkl` - Feature scaler

---

## Notes
- **EEG is highly personal**: Data from one person may not work for another
- **Session-specific**: Even the same person needs fresh data if electrode placement changes
- **Feature extraction**: Uses relative bandpower (alpha, beta, theta, delta) + temporal features
- **Artifact rejection**: Z-score > 6.0 windows are automatically rejected
