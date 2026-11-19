---
description: Propose generic improvements made in this project back to the template (opens a PR on the template repo)
---
Scope (optional): $ARGUMENTS

Goal: lessons found here improve every project, through the template. Never push to the template's main.

1. Read `.copier-answers.yml`: `_src_path` (template repo) and `_commit` (version this project is on).
   Missing -> stop and say the project isn't linked to the template (`copier copy` or add the answers file by hand).
2. Get the template at that version (`git clone <_src_path>` into `private/upstream/`, `git checkout <_commit>`) and
   diff its `template/` folder against the same paths here. Ignore files that only the project fills in
   (`ai/*` contents, `human/*`, `AGENTS.md` sections written for this project).
3. Sort each difference: **generic** (a better rule, a fixed hook bug, a sharper command, a mistake every project
   could make) or **project-specific** (names, paths, metrics, this team's choices). Only generic ones go up.
   Also read "Mistakes this project keeps making" in `AGENTS.md`: a mistake that isn't about this project's
   domain is a candidate rule for the template.
4. Show me the list (file, change, why it's generic, evidence it helped here: an iteration row, an incident, a
   number). Wait for my OK per item.
5. For the approved items: branch `upstream/<project>-<date>` on the template repo, apply them to `template/`,
   add an `Unreleased` entry in `CHANGELOG.md` with the evidence status (`tested: ...` or `untested`), open a PR.
   Report the PR link. The template owner merges and tags a release; projects get it with `copier update`.
