---
description: One improvement cycle (hypothesis -> change -> judge -> keep or revert -> log)
---
Focus (optional): $ARGUMENTS

1. Find ONE concrete weakness with the judge (worst case first), and check `ai/MECHANISMS.md` for an unexploited gap.
2. State the hypothesis in one line. Make ONE change behind a new flag whose default keeps the old behaviour.
3. Run the judge against FIXED inputs/opponents. Keep only if it helps on average and nothing important gets worse.
   For a structurally new approach: tune it a little before judging.
4. Run the tests, add one row to `ai/ITERATIONS.md` (kept or not; rejected -> also `ai/REJECTED.md` with conditions),
   commit. Report: hypothesis, numbers, decision.
