# Agent context: BCI (non-invasive brain-computer interface for virtual cursor control)

For AI coding agents. Humans: start at `human/STATUS.md`. Keep this file SHORT: current truth only.
History goes to `ai/ITERATIONS.md` and `ai/DECISIONS.md`; prune this file on every update.
Keep the top stable and put what changes often at the bottom (Status): a stable start is cached and costs ~10x less.

## Goal and metric
- Goal: <one line>
- Scoring metric (the real one, e.g. rank not profit): <...>
- Deadline / constraints: <...>

## Map
- Main code: `python_solution/` (`predict.py` live prediction, `collect.py` data collection, `diagnose.py` serial rate check); Arduino sketch `arduino_solution/01-bio_amp_512hz/`; training `notebook/create_prediction_model.ipynb`; datasets `artefacts/data/`
- Docs: `README.md`, `4CLASS_MOUSE_GUIDE.md`, `presentation.md`
- Hardware: Arduino UNO R4 + BioAmp EXG Pill, single channel A0, 512Hz, 115200 baud
- Judge / benchmark: <command> (must run in seconds; paired seeds or fixed inputs)
- `ai/MECHANISMS.md` how the system works + gaps | `ai/NOTES.md` facts, open questions, known problems
- `ai/ITERATIONS.md` every tested change | `ai/REJECTED.md` rejected ideas + conditions
- `ai/DECISIONS.md` who decided what, and on what basis
- `ai/ROLES.md` active specialist roles: when a change hits a role's inline trigger, run that role as a subagent before finishing
- `private/` your own scratch (gitignored)

## Verified commands
Only commands someone actually ran, with the date. A command that fails as committed says so.
- `<command>`: <what it does> (verified <YYYY-MM-DD>)

**NOT BUILT:** <tests? CI? deploy?>. Never present something as working until it is listed above with a date.

## Loop (one change at a time)
New behaviour = new flag, default off -> run the judge -> keep or revert -> one row in `ai/ITERATIONS.md` -> commit.
Every 3rd iteration: `/explore` (a structurally different approach, not a knob).
Continuous work (a loop, a long run, a watcher, a scraper, a context updater): post the human a very short status
every 5 minutes (1-3 lines: what runs, progress, any problem, and an ETA), e.g. a `*/5 * * * *` CronCreate job, so a
stuck agent is visible. Start each one with `### 🔄⏱️ CONT. UPDATE HH:MM` so it stands apart from conversation. Log each ETA and the actual finish in `ai/ESTIMATES.md`, and correct new ETAs by the past errors. When something finished or failed, act on it in that tick, don't only report it.

## Ask, don't guess
1. A missing input (spec, schema, definition, data) -> ask. Never infer it from a sample and proceed as if agreed.
2. Two sources disagree (code vs doc, config vs spec) -> say so and ask which wins. Never pick the nearest one.
3. No confident answer -> list what was searched and stop.
4. Before building, check whether something existing already answers the request. If it does, stop there.
5. A failed check is a correct outcome. Explain it, name who must decide, and stop. Never edit the input to make it pass.

## Rules
1. <hard constraints: time limits, no crashes, don't hard-code X ...>
2. Every action outside the repo (upload, deploy, submit) is logged at the moment it happens: what, hash, time.
3. Numbering of iterations: prefix with your name/branch to avoid collisions.
4. Irreversible actions (drop/delete/truncate, force-push, deleting cloud resources) need explicit consent first.
5. Coding: state assumptions; minimum code that solves it; touch only what the task needs; define a check before changing.

## Cost
1. Search with the `explorer` subagent (cheap model); keep the main model for decisions and code.
2. Tools before LLM: run the tests, linter or script instead of reasoning about what they would say.
3. One task per session: `/checkpoint` then `/clear` between unrelated tasks. Long sessions cost more per step.
4. `/bestofn` only for hard tasks, with the cost estimate stated first.

## Who decides (human gates)
Mode: **personal (fast)**. Speed over ceremony; the test gate and CI are the safety net.
- Agent alone: edit code, run the tests and the judge, write to `ai/`, commit, push, open a PR and **merge it itself**
  (merge commit) once the test gate and CI pass. Say what was merged.
- Needs approval: force-push, deleting branches or data, deploys and any action outside the repo, changing the judge
  or metric, spending above <$X>.
Switch mode: `uvx copier update --trust --data project_mode=client` (or `personal`).

## Mistakes this project keeps making
<Add one line each time the same mistake happens twice. This list is worth more than any general advice.>

## Status
- Current best: 4-class EEG+EOG mouse control, ~65% accuracy (ds06); binary SVM 75.5% (ds09)
- Open todos: `human/STATUS.md`
