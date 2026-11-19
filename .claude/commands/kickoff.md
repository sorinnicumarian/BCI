---
description: First-hour checklist for a new project (before any tuning)
---
Context (optional): $ARGUMENTS

1. Restate the goal and the ACTUAL scoring metric in AGENTS.md. Ask me if unclear.
2. Read every rule/spec/doc. Fill `ai/MECHANISMS.md`: one row per mechanism, mark hidden or unknown parameters,
   and say what an ideal solution would exploit.
3. List 3-5 fundamentally different approaches, including the standard textbook one for this kind of problem
   (search the literature if needed). Recommend one to start with and say why.
4. Build the judge/benchmark first (fast, uses the real metric), plus an oracle variant that can see hidden values,
   to size which unknowns are worth estimating.
5. Propose which continuous watcher loops are worth running (see `/watch`), one job each.
6. In `AGENTS.md`: fill "Verified commands" with what you actually ran (with today's date) and the NOT BUILT line;
   check "Who decides": if it has no `Mode:` line, ask me first: **personal / uni (fast)**, the agent merges its own PRs
   once checks pass, or **client / work (strict)**, a human reviews and merges every PR. Then fill it in and ask me to confirm.
   Set `TEST_GATE_CMD` in `.claude/settings.json` to the fastest check that catches a broken build (seconds, not
   minutes): the Stop hook then won't let an agent finish while it fails.
7. Put every decision made so far in `ai/DECISIONS.md`, and every open question with its owner.
8. Report: metric, top 3 gaps, chosen approach, judge command, open decisions.
9. Suggest running `/roles` next to pick the specialist roles (reviewers/testers) this project needs.
