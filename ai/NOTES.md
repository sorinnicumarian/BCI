# Notes

## Facts (with source)
- Hardware, placements, dataset history and features: `README.md` (one source of truth, not copied here).
- Datasets 06/08/09 are 4-class; 07 has only CBRight + SingLeft (not in the judge). Format: `index,value` raw ADC at 512 Hz.
- Live loop architecture (serial thread + mouse thread): `python_solution/predict.py`.

## Open questions
See `ai/DECISIONS.md` Open.

## Known problems (found, not fixed)

| # | Where | Problem | Why it matters | Proposed fix | Size |
|---|---|---|---|---|---|
| 1 | `artefacts/data/` | Each class is one contiguous recording, so drift / electrode contact differ per class | Offline accuracy may measure "which recording", not mental state (ds09 0.99 is suspicious) | Cued, interleaved recording in one file; judge splits by trial | M |
| 2 | `README.md` vs `predict.py` | README describes scipy + SVM 4-class cascade and `arduino_solution/signal.ino`; code is 2-class numpy rule, sketch is `01-bio_amp_512hz/` | Misleads agents and readers | Update README once the 4-class path is tried live | S |
| 3 | `python_solution/*.py` shebang | Points to `python_solution/.venv`, which doesn't exist | `./predict.py` fails as documented | Create the venv, or use `uv run` | S |
| 4 | `python_solution/model.pkl`, `scaler.pkl` | Not used by current `predict.py` | Stale artefacts | Delete or document | S |
