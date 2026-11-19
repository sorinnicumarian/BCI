# Decisions

| Date | Decision | Made by | Basis |
|---|---|---|---|
| 2026-11-20 | Mode personal; no issue pipeline | Sorin | template setup questions |
| 2026-11-20 | Goal = improve the 1-channel cursor (not the Epoc X pivot, which stays a todo) | Sorin | kickoff question |
| 2026-11-20 | README 4-class design is the target; 2-class `predict.py` is a temporary simplification | Sorin | kickoff question (docs vs code) |
| 2026-11-20 | Metric = offline 4-class balanced accuracy, chronological 70/30 split per recording | Sorin (metric), agent (split) | kickoff question; chronological split so overlapping windows don't leak |
| 2026-11-20 | 4-class model added behind `BCI_MODEL`, default off | agent | AGENTS.md loop rule: new behaviour = new flag |

## Open (waiting on a person)

| Q | Question | Owner | Blocks |
|---|---|---|---|
| Q1 | Record an interleaved, cued session (classes alternate every few seconds in ONE file) so the judge can rule out the recording confound? | Sorin | trusting the 0.81 |
| Q2 | Which electrode placement is current (README: outer canthus best; memory: bilateral forehead)? | Sorin | which dataset to train `model4.pkl` on |
| Q3 | Try `BCI_MODEL` live with the headset | Sorin | knowing if offline gains are real |
