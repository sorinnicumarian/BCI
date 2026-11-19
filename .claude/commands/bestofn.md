---
description: Hard task -> N independent attempts in parallel worktrees, a judge picks the best (default N=3)
---
Task: $ARGUMENTS

Use only for tasks that are hard or ambiguous (design choice, tricky bug, performance). Cost is roughly N times one
attempt, so say the estimate before starting. For simple tasks, do them once.

1. **Define "best" first.** Write the acceptance checks (tests that must pass, the judge/benchmark command, constraints
   from `AGENTS.md`) and a short rubric (correctness first, then simplicity, then size of the diff). Show them to me.
2. **Launch N attempts in parallel** (Agent tool, `isolation: "worktree"`, one per attempt, all in one message).
   Give each the same task and checks, plus a different starting angle so they don't converge on one idea
   (e.g. "minimal change", "restructure the module", "different algorithm"). They must not see each other.
3. **Judge** each worktree: run the acceptance checks yourself (don't trust the attempt's own report), then compare the
   survivors against the rubric. Use a fresh subagent as judge if the choice is close, giving it only the diffs and
   check results, not the attempts' explanations.
4. **Report** a table: attempt, approach, checks passed, diff size, cost if known, verdict. Recommend one, say why,
   and note anything worth taking from the losers.
5. Merge only the chosen worktree after I confirm. Log the run in `ai/ITERATIONS.md` (or `ai/DECISIONS.md` for a design choice).
