---
description: Trim the role catalog in ai/ROLES.md to the roles THIS project needs (run after /kickoff, re-run when the project changes)
---
Context (optional): $ARGUMENTS

Be strict. Every role costs runs, tokens and reading time; a role that produces reports nobody acts on is
negative value. Default answer for each role is **dropped**.

1. Read `AGENTS.md` (goal, metric, constraints), `ai/MECHANISMS.md`, the code layout and what is deployed where.
2. For EACH catalog role in `ai/ROLES.md`, set a status:
   - `active` only if you can name a **concrete risk or goal in this project** it addresses (not "good practice"),
     what it would look at (paths/features), and what its output would change.
   - `later` with the condition that would make it relevant (e.g. "when the app has real users").
   - `dropped` with a one-line reason.
3. Propose roles the catalog lacks that this project needs (domain-specific ones, e.g. "pricing-rule auditor").
   Add them under "Added for this project".
4. Start small: **at most 5 active roles**. If more qualify, rank by risk x likelihood and put the rest in `later`.
5. For each active role, fill the Active table: focus, **inline trigger** (which kind of change makes a working agent
   call it as a subagent), **schedule** (on PR / nightly / weekly / none) and output (issue / PR / report file).
   Inline-only and scheduled-only are both fine.
6. Ethical hacker and stress tester: only against environments this project owns, with the scope written down.
7. Record the selection in `ai/DECISIONS.md` and show me the Active table plus the `later` list. Ask me to confirm
   before anything gets scheduled.

Re-run when the project changes shape (first deploy, first users, new data, new integration): move `later` roles
whose condition is now true.
