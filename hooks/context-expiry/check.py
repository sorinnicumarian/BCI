#!/usr/bin/env python3
"""SessionStart hook: warn when facts in AGENTS.md are older than CONTEXT_MAX_AGE_DAYS (default 30).

Looks for "(verified YYYY-MM-DD)" in AGENTS.md. Stale entries are told to Claude (additionalContext) so it re-checks
them before relying on them, and shown to the user (systemMessage). Never blocks: always exits 0.
"""
import datetime as dt, json, os, re, sys
from pathlib import Path

root = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
agents = root / "AGENTS.md"
max_age = int(os.environ.get("CONTEXT_MAX_AGE_DAYS", "30"))
try:
    text = agents.read_text(encoding="utf-8")
except OSError:
    sys.exit(0)

today = dt.date.today()
stale = []
for line in text.splitlines():
    for m in re.finditer(r"verified (\d{4}-\d{2}-\d{2})", line):
        try:
            age = (today - dt.date.fromisoformat(m.group(1))).days
        except ValueError:
            continue
        if age > max_age:
            stale.append(f"- ({age} days) {line.strip()[:160]}")
if not stale:
    sys.exit(0)

msg = (f"{len(stale)} item(s) in AGENTS.md were last verified more than {max_age} days ago. "
       "Re-check them before relying on them, and update the date when they still hold:\n" + "\n".join(stale[:15]))
print(json.dumps({
    "systemMessage": f"⏳ {len(stale)} stale item(s) in AGENTS.md (> {max_age} days since verified)",
    "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": msg},
}))
sys.exit(0)
