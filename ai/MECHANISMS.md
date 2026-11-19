# Mechanisms

| Mechanism | Known / hidden | What an ideal solution exploits | What we do now | Gap |
|---|---|---|---|---|
| Up/down = VEOG + alpha/beta (relax vs count) | known | sustained-gaze DC + band powers | beta% threshold (2-class) | 4-class logreg uses both (flag) |
| Left/right = HEOG saccades + mental task | known; HEOG strength depends on placement (hidden per session) | line length / peak-to-peak on glances | not used live; logreg uses it offline | needs live test |
| Session drift / electrode contact | hidden | per-session calibration | none | judge trains per session; live model trained on one dataset may not transfer (Q2) |
| Recording-block confound | hidden | interleaved cued trials | none | Q1 |

Revisited: 2026-11-20
