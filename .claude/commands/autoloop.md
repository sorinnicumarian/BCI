---
description: Unattended optimisation loop (overnight / with /loop), only after its prerequisites exist
---
Target (optional): $ARGUMENTS

Use only when `/iterate` works by hand and you want it to run unattended (the "Karpathy loop").

## Prerequisites: check all, or build the missing one first and stop
1. **One editable surface:** exactly one file (or one named block) the loop may change.
2. **One metric:** the judge command prints one number; higher/lower is better is stated; tie-breaker named.
3. **One time budget:** per experiment (e.g. 5 min), per session (e.g. 8 h), per cost (e.g. $X).
4. **Locked judge:** the judge and its data cannot be changed by the loop. A held-out set it never sees.
5. **Revert works:** every experiment is a commit on a branch that can be dropped.
6. **Cheap failure:** not customer-facing, not production, not money or compliance.
7. **Direction:** `ai/MECHANISMS.md` gaps and `ai/REJECTED.md` say what to try and what not to.

## Loop (each experiment)
1. Read the editable surface, the direction, the last ~10 rows of `ai/ITERATIONS.md`.
2. One hypothesis, one edit. Run the judge within the budget.
3. Better on average -> commit with the delta in the message. Otherwise revert.
4. Log a row in `ai/ITERATIONS.md` either way (and `ai/REJECTED.md` with conditions if rejected).
5. Heartbeat: one line (experiment n, metric, kept/reverted), and a short status to the human every 5 minutes
   while an experiment runs (`AGENTS.md`, Loop).

## Stop when
Budget is spent, N experiments in a row give no gain, or anything outside the editable surface would need to change.

## After the loop (a human, always)
Review the top kept edits: real improvement, or gaming the metric? Re-score on the held-out set.
Nothing is promoted to production by the loop itself.
