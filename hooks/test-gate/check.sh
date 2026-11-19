#!/usr/bin/env bash
# Stop hook: the agent can't finish while the project's fast check fails.
# A rule in AGENTS.md can be ignored; this can't. Exit 2 = Claude Code blocks the stop and shows stderr to the agent.
#
# Config (env, set in .claude/settings.json):
#   TEST_GATE_CMD         fast check, e.g. "uv run pytest -q tests/test_fast.py". Empty = gate off (default).
#   TEST_GATE_MAX_BLOCKS  give up after this many blocks per session (default 3), so a stuck agent can still stop
#                         and report; the failure is then written to stderr for the human.
# Skips when the working tree has no changes (questions, reviews, planning don't pay for a test run).
set -u
[ -z "${TEST_GATE_CMD:-}" ] && exit 0

payload=$(cat)
session=$(printf '%s' "$payload" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("session_id","unknown"))' 2>/dev/null || echo unknown)
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0

# Nothing changed -> nothing to verify.
if git rev-parse --git-dir >/dev/null 2>&1 && [ -z "$(git status --porcelain --untracked-files=normal -- . ':!ai' ':!human' ':!runs' 2>/dev/null)" ]; then
  exit 0
fi

state_dir="runs/test-gate"; mkdir -p "$state_dir"
count_file="$state_dir/$session.count"
count=$(cat "$count_file" 2>/dev/null || echo 0)
max="${TEST_GATE_MAX_BLOCKS:-3}"

out=$(bash -c "$TEST_GATE_CMD" 2>&1); status=$?
if [ "$status" -eq 0 ]; then
  rm -f "$count_file"; exit 0
fi

if [ "$count" -ge "$max" ]; then
  echo "test-gate: '$TEST_GATE_CMD' still fails after $max attempts; letting the agent stop. Say so in the final message." >&2
  rm -f "$count_file"; exit 0
fi
echo $((count + 1)) > "$count_file"
{
  echo "test-gate: '$TEST_GATE_CMD' failed (exit $status). Fix it before finishing, or explain why it can't pass and stop."
  echo "Never edit tests or the check to make it pass. Attempt $((count + 1)) of $max. Last lines:"
  printf '%s\n' "$out" | tail -n 30
} >&2
exit 2
