# FinOps hook

> Copied unchanged from `tkw-internal/agent-harness-dlc` (2026-10-21). Examples below mention that
> project's skills and its `mcp__harness__*` tools; the hook itself is generic. Prices in
> `pricing.json` are dated 2026-09-29: check them before trusting dollar figures.
> Turn it off by removing the hooks from `.claude/settings.json`. On Windows, `python3` may not exist.

Records **prompt, tokens and cost** for every Claude Code session in this repo. It attributes
them to the skill that was running (`Skill` tool calls, or `/skill` slash commands) and counts
tool calls, including harness MCP tools (`mcp__harness__*`). Stdlib-only Python 3, no venv.
It is wired in `.claude/settings.json` on `UserPromptSubmit`, `PostToolUse` (matcher `Skill`),
`Stop`, `SubagentStop` and `SessionEnd`.

## What is recorded, and where

Ledger: `runs/finops/ledger.jsonl` (gitignored via `runs/`), one JSON event per line. Override the
directory with `FINOPS_DIR`.

| event | written on | contents |
|---|---|---|
| `prompt` | UserPromptSubmit | session_id, UTC ts, cwd, prompt text, char length, sha256, active skill |
| `usage` | Stop / SubagentStop | rows per (skill, model): message count, tokens (input, output, cache write 5m, cache write 1h, cache read), USD cost, flags. Also tool-call counts per skill, the `mcp__harness__*` call count and running session totals |
| `skill_summary` | PostToolUse(Skill) / Stop / SessionEnd | one skill invocation: skill, started_at, duration, messages, tokens, cost, harness calls, top tools, session cost; `status` is `done` or `turn_end` (cumulative so far) |
| `session_end` | SessionEnd | final sweep of the transcript, then session totals and the exit reason |

Per-session cursors live in `runs/finops/state/<session>.json`. They hold byte offsets plus the
assistant message ids and tool_use ids already counted. Claude Code writes one assistant message
as several transcript lines that repeat the same `usage`. The hook merges them by `message.id`
and counts each message once. Running `Stop` twice adds nothing. Errors go to
`runs/finops/errors.log`. The hook always exits 0 and prints nothing to stdout, so it never blocks
a session or injects context.

## Per-skill summaries

Claude Code has no "skill finished" event, so a skill invocation is treated as complete when:
(a) another `Skill` call starts (PostToolUse on `Skill` closes the previous invocation), or
(b) the turn stops while it is still open (a cumulative `(turn end)` summary; repeated each turn it
does more work, and a final one when it really ends), or (c) SessionEnd (ledger only). On
PostToolUse and Stop the hook prints one JSON line on stdout, `{"systemMessage": "..."}`, which
Claude Code shows to the user (not to Claude), e.g.

`💰 fabric-source-to-silver — 252k tok (in 2.0k / out 40k / cache r 200k w 10k) · $0.93 · 1 harness calls · session $1.39`

`FINOPS_SKILL_SUMMARY=0` turns the message off; the `skill_summary` events are still written.
A re-fired Stop with no new activity prints nothing.

## Privacy

By default, prompts are stored **in plain text** on this machine. Set `FINOPS_REDACT_PROMPTS=1`
to store only the sha256 and the length. Nothing is sent anywhere.

## Reading it

```
python3 hooks/finops/finops.py report                      # by skill (default)
python3 hooks/finops/finops.py report --by session|day|model|tool|invocation
python3 hooks/finops/finops.py report --session <id-prefix> --since 2026-09-01
```

Optional: set `FINOPS_SESSION_BUDGET_USD=5`. When a session's estimate goes over that amount, a
warning goes to stderr at `Stop`. It never blocks the session.

## Pricing

`pricing.json` holds Anthropic first-party list prices in USD per MTok for input, output, cache
write 5m and 1h, and cache read. They were taken on 2026-09-29 from the `claude-api` skill and the
pricing page it references (the source is recorded in the file). Model ids match on an exact id,
with an optional date or Bedrock suffix; `[1m]` is stripped. Claude 4.6+ models charge no
long-context premium, so `[1m]` uses the same rates. Fast mode (`usage.speed == "fast"`) and
US-only inference (`inference_geo == "us"`) apply their published multipliers where the
reference gives one. An unknown model, or an unpriced mode, gets `cost: null`. It is flagged and
marked `*` in the report, never guessed. Update `pricing.json` when prices change.

## Limitations

- The cost is a **list-price estimate**, not the invoice. It ignores negotiated discounts,
  Bedrock/Vertex pricing and subscription plans (on a Claude Max/Team seat, the dollars are
  notional).
- Subagent tokens come from `<session>/subagents/agent-<agent_id>.jsonl`. The `SubagentStop`
  payload gives `agent_id` but not the path, so the path is derived. If the file is not found, an
  error is logged and that subagent's tokens are not counted. This was seen live: some
  `SubagentStop` events carry an `agent_id` that has no transcript file anywhere under
  `~/.claude/projects` (they look like internal helper agents). Their tokens are invisible to this
  hook.
- A skill stays the active skill until another skill is invoked. Nothing in the transcript marks
  where a skill ends, so work after it finishes is still charged to it. A prompt is charged to
  the skill active when it was typed, or to `/skill` if the prompt starts with one. For the same
  reason an invocation's duration runs until the next skill starts (or the session ends), so it
  can include idle time between turns.
- Tokens used by hooks, compaction or other calls that never show up as assistant messages in
  the transcript are not visible.
