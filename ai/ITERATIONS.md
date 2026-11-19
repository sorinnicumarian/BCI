# Iteration log

Judge: `uv run scripts/judge.py`, metric: 4-class balanced accuracy, mean of datasets 06/08/09 (chance 0.25).
Compare against FIXED inputs; judge on averages, never one run.

| # | Change (flag=value) | Result (before -> after, worse cases) | Kept |
|---|---|---|---|
| claude-1 | Baseline: live rule in `predict.py` (beta% < 13 -> RelaxUp else FocusDown) | 0.300 (06 0.341, 08 0.308, 09 0.250); can never output Right/Left | baseline |
| claude-2 | `BCI_MODEL=model4.pkl`: 4-class logreg on 12 window features | 0.300 -> 0.813 (06 0.612, 08 0.833, 09 0.992) | yes, flag default off |
| claude-3 | Random forest on same features | 0.805, no better than logreg | no (kept in judge only) |
| claude-4 | Ablation (logreg): drop amplitude features (logvar, line length, ptp, mean) | 0.813 -> 0.646; drop band powers instead -> 0.796. Amplitude/EOG features carry most of it | info |
