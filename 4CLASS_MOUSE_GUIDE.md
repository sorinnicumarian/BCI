# 4-Class BCI Mouse Control Guide

## 🎯 What Changed

### Backups Created
- `binary_notebook/` - Original 2-class training notebook
- `binary_python_solution/` - Original 2-class racing control

### New Features
- **4-class classification** - REST, FOCUS, LEFT, RIGHT
- **Mouse control** - Cursor moves based on mental state
- **Fast predictions** - 4 predictions/second (STEP=128)

---

## 📊 Mental States

| Class | Label | Mental State | Mouse Action |
|-------|-------|--------------|--------------|
| 0 | REST | Eyes closed, relaxed | Cursor stops |
| 1 | FOCUS | Eyes open, focus on car logo | Move UP ↑ |
| 2 | LEFT | Imagine clenching LEFT FIST | Move LEFT ← |
| 3 | RIGHT | Imagine clenching RIGHT FIST | Move RIGHT → |

---

## 🚀 Training the Model

### Step 1: Open Notebook
Open `notebook/create_prediction_model.ipynb` in VS Code or Jupyter

### Step 2: Run All Cells
The notebook now:
- Loads 4 datasets (04_relax, 04_concentrate, 04_left_fist_clench, 04_right_fist_clench)
- Extracts features with STEP=256 (50% overlap for more training data)
- Trains 4-class SVM with GridSearchCV + class_weight='balanced'
- Saves `model.pkl` and `scaler.pkl` to `python_solution/`

**Expected Accuracy**: 60-75% (4-class is harder than binary)

---

## 🖱️ Running Mouse Control

```bash
cd python_solution
./predict.py
```

### Controls
- **REST** (eyes closed, relax) → Cursor stops
- **FOCUS** (stare at car logo) → Cursor moves UP ↑
- **LEFT FIST** (imagine squeezing left hand) → Cursor moves LEFT ←
- **RIGHT FIST** (imagine squeezing right hand) → Cursor moves RIGHT →

### Speed Settings
Edit `predict.py` lines 48-49:
```python
MOUSE_SPEED = 15         # pixels per prediction for left/right (higher = faster)
MOUSE_UP_SPEED = 10      # pixels per prediction for forward movement
```

For faster cursor:
```python
MOUSE_SPEED = 30
MOUSE_UP_SPEED = 20
```

### Prediction Speed
Edit `predict.py` line 45:
```python
STEP = 128   # 0.25s (4 pred/s) - current ✓
STEP = 64    # 0.125s (8 pred/s) - very fast
STEP = 256   # 0.5s (2 pred/s) - slower
```

---

## 📁 File Structure

```
BCI/
├── notebook/                      # 4-class training (current)
│   └── create_prediction_model.ipynb
├── python_solution/               # 4-class mouse control (current)
│   ├── predict.py                 # Mouse control script
│   ├── collect.py                 # Data collection
│   ├── model.pkl                  # 4-class trained model
│   └── scaler.pkl                 # Feature scaler
├── binary_notebook/               # BACKUP: 2-class racing
├── binary_python_solution/        # BACKUP: 2-class racing
├── artefacts/data/
│   ├── 04_relax.csv              # REST class
│   ├── 04_concentrate.csv        # FOCUS class
│   ├── 04_left_fist_clench.csv   # LEFT class
│   └── 04_right_fist_clench.csv  # RIGHT class
└── 4CLASS_MOUSE_GUIDE.md         # This file
```

---

## 🔧 Troubleshooting

### Low Accuracy (<60%)
1. **Re-collect training data** - Make mental states MORE distinct
2. **Check electrode placement** - Motor imagery needs C3/Cz position
3. **Practice motor imagery** - Takes time to develop the skill
4. **Increase training time** - Collect 3+ minutes per class

### Cursor Too Fast/Slow
Adjust `MOUSE_SPEED` and `MOUSE_UP_SPEED` in predict.py

### Wrong Predictions
1. **Match training conditions** - Use SAME mental approach as during data collection
2. **Stay consistent** - Same electrode placement, same focus intensity
3. **Avoid mixing states** - Don't think about left hand while focusing

### Laggy Response
- Lower `STEP` to 64 or 32 for faster predictions
- Check CPU usage - feature extraction is computation-heavy

---

## 💡 Tips for Best Performance

### During Training Data Collection
1. **REST**: Close eyes, completely empty mind, slow breathing
2. **FOCUS**: Open eyes, stare intensely at ONE object (car logo)
3. **LEFT FIST**: Close eyes, vividly imagine squeezing LEFT fist repeatedly
4. **RIGHT FIST**: Close eyes, vividly imagine squeezing RIGHT fist repeatedly

### During Live Use
- **Practice!** Motor imagery improves with repetition
- **Stay calm** - Stress affects brain signals
- **Take breaks** - Mental fatigue reduces accuracy
- **Be patient** - 4-class is significantly harder than binary

---

## 📈 Expected Performance

| Metric | Binary (Racing) | 4-Class (Mouse) |
|--------|----------------|-----------------|
| Accuracy | 82% ✓ | 60-75% |
| Response Time | 0.25s | 0.25s |
| Mental Effort | Low | Medium-High |
| Usability | Great | Good |

---

## 🔄 Switching Back to Binary Racing

To switch back to the 2-class racing game control:

```bash
# Backup current 4-class
mv notebook notebook_4class
mv python_solution python_solution_4class

# Restore binary
cp -r binary_notebook notebook
cp -r binary_python_solution python_solution

cd python_solution
./predict.py  # Now back to racing mode
```

---

## 🎮 Next Steps

1. **Train the model**: Run all cells in notebook
2. **Test mouse control**: `./predict.py`
3. **Practice motor imagery**: Takes 5-10 sessions to get good
4. **Optimize settings**: Adjust speeds and prediction frequency
5. **Collect more data**: If accuracy is low, collect 3+ minutes per class

Good luck! 🧠🖱️✨
