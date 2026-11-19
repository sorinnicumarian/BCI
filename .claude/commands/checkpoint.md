---
description: Save the hard-to-recover context of this session before /compact, /clear or a break
---
Focus (optional): $ARGUMENTS

Write a paste-ready checkpoint so the next session can continue without re-discovering anything.
Only include what is expensive to recover; skip what git, the code or AGENTS.md already shows.
Mark empty sections "(none)".

1. **Focus and branch:** what this session was about; branch, last commits, uncommitted changes.
2. **User instructions given this session:** verbatim quotes.
3. **Conclusions reached:** each with `file:line` evidence and confidence. Include dead ends ("X is not the cause, because ...").
4. **Self-corrections:** what you got wrong and the lesson.
5. **Numbers:** tests passing, judge scores, error counts, before -> after.
6. **Next action:** ONE concrete step, specific enough to start immediately.
7. **Deferred:** follow-ups not done, with why.
8. **Files that matter:** paths to read first next time.

Then: move any durable fact into the right file (`AGENTS.md` status, `ai/NOTES.md`, `ai/DECISIONS.md`).
For any "always / never / from now on" instruction, ask whether to add it to `AGENTS.md` or memory.
