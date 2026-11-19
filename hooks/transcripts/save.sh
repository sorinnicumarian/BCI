#!/usr/bin/env bash
# SessionEnd / SubagentStop hook: keep a copy of the session transcript in runs/transcripts/ (gitignored),
# so agent failures can be studied later (postmortems, "Mistakes this project keeps making", evals).
# Reads the hook payload (JSON) on stdin. Never blocks a session: always exits 0, prints nothing.
payload="$(cat)"
src=$(python3 -c 'import json,sys; d=json.loads(sys.argv[1]); print(d.get("agent_transcript_path") or d.get("transcript_path") or "")' "$payload" 2>/dev/null)
sid=$(python3 -c 'import json,sys; d=json.loads(sys.argv[1]); print(d.get("agent_id") or d.get("session_id") or "unknown")' "$payload" 2>/dev/null)
[[ -n "$src" && -f "$src" ]] || exit 0
dir="${CLAUDE_PROJECT_DIR:-.}/runs/transcripts"
mkdir -p "$dir" 2>/dev/null && cp "$src" "$dir/$(date -u +%Y-%m-%d)-${sid}.jsonl" 2>/dev/null
# keep the last 200 transcripts
ls -1t "$dir"/*.jsonl 2>/dev/null | tail -n +201 | xargs rm -f 2>/dev/null
exit 0
