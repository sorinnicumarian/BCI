---
name: data-loss-prevention
description: >-
  STOP AND VERIFY before any command or tool call that causes irreversible data loss; get explicit user
  consent first. Use for: SQL DROP/TRUNCATE or DELETE/UPDATE without a narrow WHERE; deleting files, buckets,
  blobs, containers, databases, tables, cloud resources or resource groups; git push --force, git reset --hard,
  branch deletion with unmerged work; overwriting a table or dataset outside the designed pipeline; one-way
  migrations or upgrades. When in doubt, ask.
---

# Data loss prevention

1. **Halt.** Do not run the command.
2. **Explain** to the user: exactly what will be lost (name the target and its size or row count, which you
   looked at first), why you think it is necessary, and whether a backup or undo exists.
3. **Wait** for clear, affirmative consent in the conversation. Consent covers this one action, not similar ones later.

Not covered: the project's own designed, idempotent writes (e.g. a pipeline that replaces one partition it
owns, a build that cleans its own output folder). Those are reviewed behaviour, not ad-hoc deletion.
