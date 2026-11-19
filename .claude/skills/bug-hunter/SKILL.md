---
name: bug-hunter
description: >-
  Adversarial bug hunting for web applications — finds real, reachable defects in frontend and
  backend code and in the seam between them, then tries hard to disprove each one before reporting
  it. Runs three isolated roles: a Hunter biased to over-report, a Skeptic biased to dismiss, and a
  Referee that reads the code fresh and rules. Finds the bug classes that per-file review misses:
  API contract drift between client and server, authorization enforced in the UI but not the
  handler, tenant scoping missing on one endpoint out of many, optimistic updates that never roll
  back on failure, swallowed errors that render as success, check-then-act races, lost updates,
  double-submit and retry non-idempotency, N+1 queries behind a list view, stale cache after
  mutation, money and timezone corruption across serialization boundaries, unhandled rejections,
  and resource leaks. Works on whatever scope you point it at — uncommitted work, a branch diff, a
  single file or directory, or a whole-repository audit with risk triage. Use this skill whenever
  someone asks to find bugs, hunt for bugs, audit or review code for defects, check what might be
  broken before shipping or merging, sanity-check a PR or branch, asks "is there anything wrong
  with this", "what could break here", "does this look right", "something feels off about this
  code", "why might this be flaky", or wants a second pair of eyes on code they just wrote — even
  when they don't use the word "bug". Also use it proactively after implementing a non-trivial
  feature that touches auth, money, tenancy, concurrency, or client/server data flow. It reports
  only and never edits code. It is for finding unknown defects; for diagnosing one specific error
  the user is already staring at, debug directly instead.
---

# Bug Hunter

Bug scans by a single reader fail in a predictable way. The reader pattern-matches — "this query is built with string concatenation", "this promise has no catch" — and reports the match. Then half the findings turn out to be unreachable, already guarded three layers up, deliberate, or in a test fixture. A report where half the entries are wrong is worse than no report: the user stops trusting the other half.

This skill exists to solve that one problem. It doesn't ask an agent to be careful and accurate — an agent asked for accuracy splits the difference and produces mush, hedging on real bugs and hedging equally on imaginary ones. Instead it runs two agents with *opposed* biases and makes them argue with evidence, then has a third read the code cold and rule. Calibration comes out of the disagreement, not out of any one agent's judgment.

The second thing this skill is for: **the seam**. In a webapp, the expensive bugs usually don't live inside a file. They live between the client's assumption and the server's behavior — the field that's nullable in the database and dereferenced in the component, the permission check the button hides but the endpoint doesn't enforce, the list the API truncates and the UI paginates as if it were complete. Nobody reviewing one file at a time finds these. One Hunter is assigned to nothing else.

## Ground rules

**Report only.** Never edit code during a hunt, not even an obvious one-line fix. The value of the report is that the user can trust every line of it was produced by looking, not by changing. If they want fixes afterward, that's a separate request — offer it at the end.

**A finding needs a trigger.** Every reported bug must include a concrete path from something a real user or system actually does to the failure. "This could be null" is not a finding. "`GET /api/reports` returns `assignee: null` for unassigned reports (repo.ts:88, no default), and `ReportRow` dereferences `assignee.name` (ReportRow.tsx:34) — the list crashes as soon as one report is unassigned" is a finding. If you can't write the trigger, you don't have a bug; you have a smell. Smells go in a separate, clearly-labeled section or nowhere.

**Prove nothing prevents it.** The single largest source of false positives is a guard the reader didn't look for — middleware, a validation layer, a framework default, a type constraint, a database check. Before a finding is reported, someone must have gone looking for the guard and not found it. That's most of the Skeptic's job.

## Step 1 — Settle the scope

Don't ask which scope unless it's genuinely ambiguous; infer it and say what you chose in one line, so the user can redirect cheaply.

- Named files, directories, or a component → hunt exactly that, plus whatever it calls and whatever calls it.
- "What I just wrote", "before I commit", "check my changes" → `git diff` plus `git status` for uncommitted work.
- "My PR", "this branch", "before I merge" → `git diff <base>...HEAD`. Find the base branch rather than assuming `main`.
- "Audit the app", "find bugs in this codebase", no scope given in a repo they clearly want reviewed → whole repo, which means triage (below).
- Nothing obvious → default to uncommitted + branch diff, and say so. It's the cheap, high-signal read, and widening later costs one message.

For diff scopes, always read the **whole file** around each changed hunk, not the hunk alone. A diff hides the bug it causes: the line that changed is fine, and the line 40 rows down that depended on the old behavior is the bug.

## Step 2 — Recon (do this yourself, don't delegate)

Spend a few minutes building a map before spawning anything. Hunters that don't know the app's shape waste their budget rediscovering it, and five of them rediscovering it in parallel is five times the waste.

Establish and write down:

- **Stack and versions** — from `package.json`, `*.csproj`, `pyproject.toml`, `go.mod`, `Gemfile`. Framework version decides what's a bug: React 18's automatic batching, .NET's nullable reference types, an ORM that parameterizes by default. Guessing here manufactures false positives.
- **Entry points** — routes, controllers, handlers, server actions, GraphQL resolvers, webhooks, background jobs, cron. Every bug that matters is reachable from one of these; that's what makes a trigger writable.
- **Trust boundaries** — where unauthenticated input arrives, where authentication is established, where authorization is *supposed* to be enforced, where the tenant/org/user scope is applied. Note the mechanism, so a Hunter can check whether a given handler actually uses it.
- **The contract** — how the client learns the server's shapes. Generated types, a shared package, an OpenAPI spec, or hand-written interfaces that drift. Hand-written and unvalidated is itself a finding waiting to happen, and tells you where to look hardest.
- **What's actually at stake** — money, PII, tenancy, anything destructive. Severity is about consequence, and consequence is domain-specific.

For a whole-repo scope, add **risk triage** — you can't read everything, and pretending otherwise produces a shallow pass over a wide area, which is the worst possible use of the budget. Rank files by: reachability from an entry point, whether they touch auth/money/tenancy/destructive operations, recent churn (`git log --since='3 months ago' --name-only | sort | uniq -c | sort -rn`), and fan-in. Hunt the top slice properly rather than everything badly, and say in the report what you didn't cover. Silent truncation reads as "I checked everything" when you didn't.

## Step 3 — Hunt

Spawn Hunters in parallel, one per territory, in a single message. Each gets `references/hunter-brief.md`, `references/hunting-grounds.md`, your recon map, and its territory.

Default territories for a broad scope — collapse to two or three for a small diff, and drop any the codebase doesn't have:

1. **Entry points and authorization** — every route/handler/action: authentication, authorization, tenant scoping, input validation, mass assignment, rate limits.
2. **Data and persistence** — queries, transactions, migrations, constraints, ORM behavior, N+1, lost updates, nullability as the database actually defines it.
3. **Client state and data flow** — fetching, caching, effects, forms, optimistic updates, loading and error states, stale closures, unmounted writes.
4. **The seam** — client assumptions versus server behavior. Contract drift, error-path handling, serialization of money/dates/decimals/IDs, pagination and filtering split across the boundary, auth assumed on the wrong side.
5. **Async, concurrency, and integrations** — jobs, webhooks, retries, timeouts, idempotency, races, unhandled rejections, leaked resources.

Use `general-purpose` subagents. **Do not use `fork`** — a fork inherits this conversation, which destroys the independence the whole design rests on. The Hunter must reach its conclusions from the code, not from yours.

Hunters are told to over-report. That's deliberate and you should not correct for it here — filtering happens next, by an agent whose job is filtering. If you pre-filter, you've collapsed the design back into a single biased reader.

Deduplicate the returned findings by (file, line, claim) before proceeding; territories overlap on purpose and the same bug will arrive twice.

## Step 4 — Skeptic

For each surviving finding, spawn a Skeptic subagent with `references/skeptic-brief.md` and **the claim alone** — location, trigger, consequence, evidence lines. Not the Hunter's reasoning, not its confidence, not its narrative. Anchoring is the failure mode here: a Skeptic shown a persuasive argument evaluates the argument instead of the code.

The Skeptic's job is to refute: find the guard, prove the path is unreachable, show the framework handles it, show it's test-only or dead. It returns `REFUTED` with evidence, or `STANDS` with a note on what it checked and failed to find.

Batch related findings into one Skeptic when they share a file and mechanism — separate contexts per finding is the ideal, but twenty subagents for twenty findings in one file is waste. Cap the fleet at a dozen or so and batch the tail.

A Skeptic that refutes with concrete counter-evidence — a named middleware, a specific validation call, the actual framework behavior — settles Low and Medium findings on its own. Drop them. The Referee is the expensive tiebreaker; spend it where it changes the answer.

## Step 5 — Referee

Send to the Referee, with `references/referee-brief.md`:

- every finding where Hunter and Skeptic disagree (Hunter claims, Skeptic refutes), and
- every Critical and High finding, including ones the Skeptic let stand — the cost of a wrong Critical is high in both directions.

The Referee gets the claim and the refutation stripped to evidence — locations and code, no rhetoric — and reads the code itself. It answers one question: does the trigger actually reach the failure in this codebase as written? Verdicts are `REAL_BUG`, `NOT_A_BUG`, or `NEEDS_HUMAN` (for things that turn on intent, product decisions, or runtime facts unavailable from source — an external service's actual behavior, whether a race window is reachable at real traffic).

The Referee also re-scores severity. Hunters inflate; the Referee owns the number that ends up in the report.

## Step 6 — Report

Write the report to the conversation. Only add a file if the user asks or if it's long enough to be unusable inline.

```markdown
# Bug hunt — <scope in a few words>

<Stack>. <N> files examined. **<X> confirmed** · <Y> dismissed · <Z> need a human.
<One line naming anything deliberately not covered.>

## Confirmed

### 1. [Critical] <what breaks, in one line>
**Where:** `path/to/file.ts:88` (and `other/file.tsx:34`)
**Trigger:** <the concrete path from a real action to the failure>
**Consequence:** <what the user, the data, or the system experiences>
**Evidence:**
```<lang>
<the few lines that prove it, from each file involved>
```
**Survived review because:** <what the Skeptic argued, and why it didn't hold>
**Fix direction:** <one or two sentences — where the fix goes, not a patch>
**Confidence:** High | Medium

## Needs a human
### <title> — `path:line`
<The claim, and the specific question only a person can answer.>

## Dismissed
One line each: the claim, and the evidence that killed it.
- `path:line` — <claim>. Guarded by `requireOrg` middleware (middleware/auth.ts:22).
```

Severity is consequence, not category:

| | |
|---|---|
| **Critical** | Data loss or corruption, cross-tenant or cross-user data exposure, auth bypass, injection reachable from unauthenticated input, money computed wrong, crash on a common path. |
| **High** | A real defect on a path users hit: wrong data shown, a write that silently fails, a request that can't complete, a missing authorization check behind login, a race that corrupts state under ordinary concurrency. |
| **Medium** | Reachable but narrower — an edge case, degradation under load, an error swallowed so the user sees nothing happen. |
| **Low** | Narrow edge case, defensive gap, wrong-but-harmless behavior. |

Confidence is a separate axis and belongs in the report: a High-severity finding at Medium confidence is worth a person's time to check, and saying so honestly is what keeps the report trustworthy. Report anything Referee-confirmed at Low confidence under **Needs a human**, not under Confirmed.

Sort by severity, then confidence. Keep **Dismissed** — it shows what was checked, stops the user from re-reporting the same thing, and is the section that earns trust in the rest.

If the hunt finds nothing, say so plainly and list what was examined. A clean report from a real search is a useful result; padding it with style nits to look productive destroys the signal the whole design exists to produce.

Close by offering fixes as a separate step. Don't start fixing.

## Reference files

- `references/hunting-grounds.md` — where webapp bugs actually live, by territory. Read it yourself during recon if the stack is unfamiliar; Hunters always get it.
- `references/hunter-brief.md` — the Hunter role and finding format.
- `references/skeptic-brief.md` — the Skeptic role and the exclusion list of things that are not bugs.
- `references/referee-brief.md` — the Referee role, verdicts, and severity calibration.

The briefs are separate files on purpose. If the Hunter could read the Skeptic's exclusion list it would self-censor, and the over-reporting bias that makes the whole thing work would quietly disappear.
