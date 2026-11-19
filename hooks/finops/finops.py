#!/usr/bin/env python3
"""FinOps hook for Claude Code: prompts, tokens and cost per session, per skill.

Stdlib only. Two entry points:

  python3 hooks/finops/finops.py hook      # called by Claude Code (stdin = hook JSON)
  python3 hooks/finops/finops.py report [--session ID] [--since YYYY-MM-DD]
                                        [--by skill|session|day|model|tool|invocation]

Ledger: $FINOPS_DIR (default <repo>/runs/finops)/ledger.jsonl, one JSON event per line.
The hook never blocks the session: every error goes to errors.log and it always exits 0.
Its only stdout is one {"systemMessage": ...} JSON line with per-skill summaries on
PostToolUse(Skill) / Stop (disable with FINOPS_SKILL_SUMMARY=0).
See README.md in this directory.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import json
import os
import re
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PRICING_PATH = os.path.join(HERE, "pricing.json")
TOKEN_KEYS = ("input", "output", "cache_write_5m", "cache_write_1h", "cache_read")
MTOK = 1_000_000


# --------------------------------------------------------------------------- paths / io

def finops_dir() -> str:
    return os.environ.get("FINOPS_DIR") or os.path.join(ROOT, "runs", "finops")


def ledger_path() -> str:
    return os.path.join(finops_dir(), "ledger.jsonl")


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def log_error(msg: str) -> None:
    try:
        os.makedirs(finops_dir(), exist_ok=True)
        with open(os.path.join(finops_dir(), "errors.log"), "a", encoding="utf-8") as f:
            f.write(f"{now_utc()} {msg}\n")
    except Exception:
        pass


@contextlib.contextmanager
def locked(name: str):
    """Advisory exclusive lock (Stop and SubagentStop can fire concurrently)."""
    os.makedirs(finops_dir(), exist_ok=True)
    fh = open(os.path.join(finops_dir(), name + ".lock"), "a+")
    try:
        try:
            import fcntl
            fcntl.flock(fh, fcntl.LOCK_EX)
        except ImportError:  # non-POSIX: best effort, no lock
            pass
        yield
    finally:
        fh.close()


def append_event(event: dict) -> None:
    os.makedirs(finops_dir(), exist_ok=True)
    line = json.dumps(event, separators=(",", ":"), ensure_ascii=False)
    with locked("ledger"), open(ledger_path(), "a", encoding="utf-8") as f:
        f.write(line + "\n")


def safe_id(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", s or "unknown")[:128]


def state_path(session_id: str) -> str:
    return os.path.join(finops_dir(), "state", safe_id(session_id) + ".json")


def load_state(session_id: str) -> dict:
    try:
        with open(state_path(session_id), encoding="utf-8") as f:
            st = json.load(f)
    except (FileNotFoundError, ValueError):
        st = {}
    st.setdefault("offsets", {})      # transcript path -> byte offset already read
    st.setdefault("seen_msgs", [])    # assistant message ids already counted
    st.setdefault("seen_tools", [])   # tool_use ids already counted
    st.setdefault("active_skill", None)
    st.setdefault("active_inv", None)       # open skill invocation id
    st.setdefault("invocations", {})       # open (or closed, not yet reported) invocations
    st.setdefault("closed_pending", [])    # closed invocations awaiting a final summary
    st.setdefault("totals", {"tokens": {k: 0 for k in TOKEN_KEYS}, "cost_usd": 0.0,
                             "unpriced_messages": 0, "messages": 0, "prompts": 0})
    return st


def save_state(session_id: str, st: dict) -> None:
    p = state_path(session_id)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f)
    os.replace(tmp, p)


# --------------------------------------------------------------------------- pricing

_PRICING = None
_SUFFIX_RE = re.compile(r"^([-@]\d{8})?(-v\d+(:\d+)?)?$")


def pricing() -> dict:
    global _PRICING
    if _PRICING is None:
        with open(PRICING_PATH, encoding="utf-8") as f:
            _PRICING = json.load(f)["models"]
    return _PRICING


def normalise_model(model: str) -> str:
    m = (model or "").strip().lower()
    m = re.sub(r"\[.*?\]$", "", m)                 # claude-opus-5-5[1m] -> claude-opus-5-5
    m = re.sub(r"^([a-z]{2,4}\.)?anthropic\.", "", m)  # bedrock prefixes
    return m


def resolve_model(model: str):
    """Return (pricing_key, rates) or (None, None). Exact id or id + date/version suffix only."""
    m = normalise_model(model)
    best = None
    for key in pricing():
        if m.startswith(key) and _SUFFIX_RE.match(m[len(key):]):
            if best is None or len(key) > len(best):
                best = key
    return (best, pricing()[best]) if best else (None, None)


def usage_tokens(usage: dict) -> dict:
    """Split a Messages API usage object into the five billed token categories."""
    u = usage or {}
    cc = u.get("cache_creation") or {}
    w5 = cc.get("ephemeral_5m_input_tokens")
    w1 = cc.get("ephemeral_1h_input_tokens")
    total_w = int(u.get("cache_creation_input_tokens") or 0)
    if w5 is None and w1 is None:
        w5, w1 = total_w, 0            # no TTL breakdown: 5m is the API default TTL
    else:
        w5, w1 = int(w5 or 0), int(w1 or 0)
        if w5 + w1 < total_w:          # breakdown incomplete: remainder at 5m
            w5 += total_w - (w5 + w1)
    return {
        "input": int(u.get("input_tokens") or 0),
        "output": int(u.get("output_tokens") or 0),
        "cache_write_5m": w5,
        "cache_write_1h": w1,
        "cache_read": int(u.get("cache_read_input_tokens") or 0),
    }


def price(model: str, toks: dict, usage: dict):
    """Return (cost_usd or None, pricing_key or None, flags list)."""
    flags = []
    key, r = resolve_model(model)
    if not r:
        return None, None, ["unknown_model"]
    mult = 1.0
    if (usage or {}).get("speed") == "fast":
        if r.get("fast_mode_multiplier"):
            mult *= r["fast_mode_multiplier"]
        else:
            return None, key, ["fast_mode_unpriced"]
    if (usage or {}).get("inference_geo") == "us":
        if r.get("us_inference_geo_multiplier"):
            mult *= r["us_inference_geo_multiplier"]
        else:
            flags.append("inference_geo_us_unpriced")
    cost = sum(toks[k] * r[k] for k in TOKEN_KEYS) / MTOK * mult
    return cost, key, flags


# --------------------------------------------------------------------------- transcript parsing

_CMD_RE = re.compile(r"<command-name>/?([^<\s]+)</command-name>")


def read_new_lines(path: str, offset: int):
    """Yield (json_obj) for complete lines after offset; return new offset via list."""
    out = []
    size = os.path.getsize(path)
    if offset > size:          # transcript rewritten/truncated: start over (dedupe protects)
        offset = 0
    with open(path, "rb") as f:
        f.seek(offset)
        data = f.read()
    end = data.rfind(b"\n")
    if end < 0:
        return out, offset
    for raw in data[: end + 1].splitlines():
        if not raw.strip():
            continue
        try:
            out.append(json.loads(raw))
        except ValueError:
            continue
    return out, offset + end + 1


def user_command(obj: dict):
    """Slash-command skill invocation typed by the user, e.g. /intent -> 'intent'."""
    msg = obj.get("message") or {}
    content = msg.get("content")
    texts = []
    if isinstance(content, str):
        texts.append(content)
    elif isinstance(content, list):
        texts += [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
    for t in texts:
        m = _CMD_RE.search(t or "")
        if m:
            return m.group(1)
    return None


def _parse_ts(s):
    try:
        return dt.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _new_inv(st: dict, inv_id: str, skill: str, ts, path: str, closed: list) -> None:
    """Close the open skill invocation (if any) and open a new one."""
    cur = st["active_inv"]
    if cur and cur in st["invocations"]:
        inv = st["invocations"][cur]
        inv["ended_at"] = ts or inv.get("last_ts")
        inv["closed"] = True
        closed.append(cur)
    st["invocations"][inv_id] = {
        "id": inv_id, "skill": skill, "started_at": ts, "last_ts": ts, "ended_at": None,
        "closed": False, "messages": 0, "unpriced_messages": 0, "cost_usd": 0.0,
        "tokens": {k: 0 for k in TOKEN_KEYS}, "tools": {}, "reported_messages": 0,
        "reported_tools": 0, "transcript": path}
    st["active_inv"] = inv_id
    st["active_skill"] = skill


def process_transcript(path: str, st: dict, agent: str | None):
    """Account every not-yet-counted assistant message in path. Mutates st.

    Returns (rows, tool_counts, n_messages, closed_invocation_ids). Rows are keyed by
    (skill, model). Only the main transcript (agent is None) opens or closes skill
    invocations; a subagent's usage is charged to the parent's open invocation.
    """
    offset = int(st["offsets"].get(path, 0))
    objs, new_offset = read_new_lines(path, offset)
    seen_msgs = set(st["seen_msgs"])
    seen_tools = set(st["seen_tools"])

    # Pass 1: merge split lines of one assistant message (same message.id); keep the
    # line with the largest usage (lines repeat the same usage, or grow while streaming).
    order, merged = [], {}
    for i, o in enumerate(objs):
        t = o.get("type")
        if t == "user":
            cmd = user_command(o)
            if cmd:
                order.append(("skill", cmd, o))
            continue
        if t != "assistant":
            continue
        msg = o.get("message") or {}
        mid = msg.get("id") or o.get("requestId") or o.get("uuid") or f"{path}:{offset}:{i}"
        if mid not in merged:
            merged[mid] = {"model": msg.get("model"), "usage": msg.get("usage") or {},
                           "tools": [], "sidechain": bool(o.get("isSidechain")),
                           "ts": o.get("timestamp")}
            order.append(("msg", mid, o))
        rec = merged[mid]
        u = msg.get("usage") or {}
        if (u.get("output_tokens") or 0) >= (rec["usage"].get("output_tokens") or 0):
            rec["usage"] = u
        for b in msg.get("content") or []:
            if isinstance(b, dict) and b.get("type") == "tool_use":
                rec["tools"].append(b)

    rows, tool_counts, n, closed = {}, {}, 0, []
    for kind, val, obj in order:
        if kind == "skill":
            key = "cmd:" + str(obj.get("uuid") or obj.get("timestamp") or val)
            if agent is None and key not in seen_tools:
                seen_tools.add(key)
                _new_inv(st, key, val, obj.get("timestamp"), path, closed)
            continue
        rec = merged[val]
        # A Skill call opens a new invocation; the calling message belongs to it.
        for b in rec["tools"]:
            if b.get("name") != "Skill" or agent is not None:
                continue
            sk = (b.get("input") or {}).get("skill") or (b.get("input") or {}).get("command")
            tid = b.get("id") or f"{val}:Skill"
            if sk and tid not in seen_tools:
                _new_inv(st, tid, str(sk).lstrip("/"), rec["ts"], path, closed)
        skill = st["active_skill"] or "(none)"
        inv = st["invocations"].get(st["active_inv"]) if st["active_inv"] else None
        if inv is not None and rec["ts"]:
            inv["last_ts"] = rec["ts"]
        for b in rec["tools"]:
            tid = b.get("id") or f"{val}:{b.get('name')}"
            if tid in seen_tools:
                continue
            seen_tools.add(tid)
            nm = b.get("name") or "?"
            if nm == "Skill":
                nm = "Skill:" + str((b.get("input") or {}).get("skill") or "?")
            tool_counts.setdefault(skill, {})
            tool_counts[skill][nm] = tool_counts[skill].get(nm, 0) + 1
            if inv is not None:
                inv["tools"][nm] = inv["tools"].get(nm, 0) + 1
        if val in seen_msgs:
            continue
        seen_msgs.add(val)
        toks = usage_tokens(rec["usage"])
        if not any(toks.values()):
            continue  # synthetic / error lines carry no billable usage
        model = rec["model"] or "(unknown)"
        cost, pkey, flags = price(model, toks, rec["usage"])
        k = (skill, model)
        row = rows.setdefault(k, {"skill": skill, "model": model, "pricing_key": pkey,
                                  "messages": 0, "tokens": {x: 0 for x in TOKEN_KEYS},
                                  "cost_usd": 0.0, "unpriced_messages": 0, "flags": [],
                                  "agent": agent or ("sidechain" if rec["sidechain"] else "main")})
        row["messages"] += 1
        n += 1
        for x in TOKEN_KEYS:
            row["tokens"][x] += toks[x]
        if cost is None:
            row["unpriced_messages"] += 1
        else:
            row["cost_usd"] += cost
        for fl in flags:
            if fl not in row["flags"]:
                row["flags"].append(fl)
        if inv is not None:
            inv["messages"] += 1
            for x in TOKEN_KEYS:
                inv["tokens"][x] += toks[x]
            if cost is None:
                inv["unpriced_messages"] += 1
            else:
                inv["cost_usd"] += cost

    st["offsets"][path] = new_offset
    st["seen_msgs"] = list(seen_msgs)
    st["seen_tools"] = list(seen_tools)
    return list(rows.values()), tool_counts, n, closed


def subagent_transcript(payload: dict):
    p = payload.get("agent_transcript_path")
    if p and os.path.exists(p):
        return p
    tp, aid, sid = payload.get("transcript_path"), payload.get("agent_id"), payload.get("session_id")
    if tp and aid:
        base = os.path.splitext(tp)[0]  # <project>/<session>.jsonl -> <project>/<session>/
        for cand in (os.path.join(base, "subagents", f"agent-{aid}.jsonl"),
                     os.path.join(os.path.dirname(tp), sid or "", "subagents", f"agent-{aid}.jsonl")):
            if os.path.exists(cand):
                return cand
    return None


# --------------------------------------------------------------------------- skill summaries

def _k(n: float) -> str:
    n = float(n)
    for div, suf in ((1e9, "B"), (1e6, "M"), (1e3, "k")):
        if abs(n) >= div:
            v = n / div
            return (f"{v:.1f}" if v < 10 else f"{v:.0f}") + suf
    return f"{int(n)}"


def skill_summary(sid: str, st: dict, inv_id: str, status: str, hook: str):
    """Build (ledger event, one-line user message) for one skill invocation.

    status: 'done' (the invocation ended) or 'turn_end' (cumulative so far, still open).
    """
    inv = st["invocations"][inv_id]
    t = inv["tokens"]
    start = _parse_ts(inv.get("started_at"))
    end = _parse_ts(inv.get("ended_at") if status == "done" and inv.get("ended_at") else inv.get("last_ts"))
    duration = round((end - start).total_seconds(), 1) if start and end else None
    tools = sorted(inv["tools"].items(), key=lambda kv: (-kv[1], kv[0]))
    harness = sum(c for nm, c in inv["tools"].items() if nm.startswith("mcp__harness__"))
    total_tok = sum(t.values())
    tot = st["totals"]
    ev = {"event": "skill_summary", "ts": now_utc(), "session_id": sid, "hook": hook,
          "invocation_id": inv_id, "skill": inv["skill"], "status": status,
          "started_at": inv.get("started_at"),
          "ended_at": inv.get("ended_at") if status == "done" else None,
          "duration_s": duration, "messages": inv["messages"], "tokens": dict(t),
          "total_tokens": total_tok, "cost_usd": round(inv["cost_usd"], 6),
          "unpriced_messages": inv["unpriced_messages"],
          "harness_tool_calls": harness, "top_tools": dict(tools[:8]),
          "session_cost_usd": round(tot["cost_usd"], 6)}
    label = " (turn end)" if status == "turn_end" else ""
    star = "*" if inv["unpriced_messages"] else ""
    line = (f"\U0001F4B0 {inv['skill']}{label} — {_k(total_tok)} tok "
            f"(in {_k(t['input'])} / out {_k(t['output'])} / cache r {_k(t['cache_read'])} "
            f"w {_k(t['cache_write_5m'] + t['cache_write_1h'])}) · ${inv['cost_usd']:.2f}{star} "
            f"· {harness} harness calls · session ${tot['cost_usd']:.2f}")
    return ev, line


# --------------------------------------------------------------------------- hook handlers

def on_prompt(p: dict) -> None:
    sid = p.get("session_id") or "unknown"
    prompt = p.get("prompt")
    if prompt is None:
        prompt = p.get("prompt_text") or ""
    redact = os.environ.get("FINOPS_REDACT_PROMPTS") == "1"
    with locked("state-" + safe_id(sid)):
        st = load_state(sid)
        st["totals"]["prompts"] += 1
        skill = st["active_skill"]
        cmd = _CMD_RE.search(prompt) or re.match(r"^/([A-Za-z0-9_:.-]+)", prompt.strip())
        if cmd:
            skill = cmd.group(1)
        save_state(sid, st)
    ev = {"event": "prompt", "ts": now_utc(), "session_id": sid, "cwd": p.get("cwd"),
          "prompt_id": p.get("prompt_id"), "active_skill": skill,
          "prompt_chars": len(prompt), "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
          "prompt": None if redact else prompt, "redacted": redact}
    append_event(ev)


def account(p: dict, event_name: str):
    """Account new transcript usage; return (session_totals, [(summary_event, line)])."""
    sid = p.get("session_id") or "unknown"
    paths, agent = [], None
    if event_name == "SubagentStop":
        agent = p.get("agent_type") or p.get("agent_id") or "subagent"
        sp = subagent_transcript(p)
        if sp:
            paths.append(sp)
        else:
            log_error(f"SubagentStop {sid}: no subagent transcript found "
                      f"(agent_id={p.get('agent_id')}); its tokens are not counted")
    else:
        tp = p.get("transcript_path")
        if tp and os.path.exists(tp):
            paths.append(tp)
    summaries = []
    with locked("state-" + safe_id(sid)):
        st = load_state(sid)
        all_rows, all_tools, n = [], {}, 0
        for path in paths:
            rows, tools, k, closed = process_transcript(path, st, agent)
            st["closed_pending"] += [c for c in closed if c not in st["closed_pending"]]
            all_rows += rows
            n += k
            for sk, d in tools.items():
                for nm, c in d.items():
                    all_tools.setdefault(sk, {})
                    all_tools[sk][nm] = all_tools[sk].get(nm, 0) + c
        tot = st["totals"]
        for r in all_rows:
            for x in TOKEN_KEYS:
                tot["tokens"][x] += r["tokens"][x]
            tot["cost_usd"] += r["cost_usd"]
            tot["unpriced_messages"] += r["unpriced_messages"]
            tot["messages"] += r["messages"]

        # Skill completion: (a) a new Skill started -> previous invocation closed;
        # (b) Stop -> cumulative "(turn end)" for the still-open invocation if it had
        # activity since its last report; (c) SessionEnd -> close the open invocation.
        if event_name in ("PostToolUse", "Stop", "SessionEnd"):
            if event_name == "SessionEnd" and st["active_inv"] in st["invocations"]:
                inv = st["invocations"][st["active_inv"]]
                inv["closed"], inv["ended_at"] = True, inv.get("last_ts")
                st["closed_pending"].append(st["active_inv"])
                st["active_inv"] = None
            for inv_id in st["closed_pending"]:
                if inv_id in st["invocations"]:
                    summaries.append(skill_summary(sid, st, inv_id, "done", event_name))
                    del st["invocations"][inv_id]
            st["closed_pending"] = []
            if event_name == "Stop" and st["active_inv"] in st["invocations"]:
                inv = st["invocations"][st["active_inv"]]
                ntools = sum(inv["tools"].values())
                if inv["messages"] > inv["reported_messages"] or ntools > inv["reported_tools"]:
                    summaries.append(skill_summary(sid, st, st["active_inv"], "turn_end", event_name))
                    inv["reported_messages"], inv["reported_tools"] = inv["messages"], ntools
        save_state(sid, st)
        totals = json.loads(json.dumps(tot))
        active = st["active_skill"]
    if all_rows or all_tools:
        append_event({"event": "usage", "ts": now_utc(), "session_id": sid, "hook": event_name,
                      "agent": agent, "active_skill": active, "messages": n,
                      "rows": [dict(r, cost_usd=round(r["cost_usd"], 6)) for r in all_rows],
                      "cost_usd": round(sum(r["cost_usd"] for r in all_rows), 6),
                      "tool_calls": all_tools,
                      "harness_tool_calls": sum(c for d in all_tools.values() for nm, c in d.items()
                                                if nm.startswith("mcp__harness__")),
                      "session_totals": dict(totals, cost_usd=round(totals["cost_usd"], 6))})
    for ev, _ in summaries:
        append_event(ev)
    return (totals if paths else None), summaries


def budget_check(totals: dict | None) -> None:
    b = os.environ.get("FINOPS_SESSION_BUDGET_USD")
    if not b or not totals:
        return
    try:
        limit = float(b)
    except ValueError:
        return
    if totals["cost_usd"] > limit:
        toks = sum(totals.get("tokens", {}).values())
        sys.stderr.write(f"[finops] session used {toks:,} tokens, ${totals['cost_usd']:.2f} at API prices, "
                         f"over FINOPS_SESSION_BUDGET_USD=${limit:.2f}\n")


def on_session_end(p: dict) -> None:
    sid = p.get("session_id") or "unknown"
    account(p, "SessionEnd")  # sweep anything a missed Stop left behind, close open skill
    with locked("state-" + safe_id(sid)):
        st = load_state(sid)
        totals = st["totals"]
    append_event({"event": "session_end", "ts": now_utc(), "session_id": sid, "cwd": p.get("cwd"),
                  "reason": p.get("reason") or p.get("exit_reason"),
                  "last_active_skill": st["active_skill"],
                  "session_totals": dict(totals, cost_usd=round(totals["cost_usd"], 6))})


def cmd_hook() -> int:
    out = None
    try:
        raw = sys.stdin.read()
        p = json.loads(raw) if raw.strip() else {}
        ev = p.get("hook_event_name")
        summaries = []
        if ev == "UserPromptSubmit":
            on_prompt(p)
        elif ev == "PostToolUse":
            # Main-thread Skill calls only; a subagent's tokens arrive via SubagentStop.
            if p.get("tool_name") == "Skill" and not p.get("agent_id"):
                _, summaries = account(p, ev)
        elif ev in ("Stop", "SubagentStop"):
            totals, summaries = account(p, ev)
            budget_check(totals)
        elif ev == "SessionEnd":
            on_session_end(p)
        if summaries and ev in ("PostToolUse", "Stop") and os.environ.get("FINOPS_SKILL_SUMMARY", "1") != "0":
            out = json.dumps({"systemMessage": "\n".join(line for _, line in summaries)},
                             ensure_ascii=False)
    except Exception:
        log_error("hook failed: " + traceback.format_exc().replace("\n", " | "))
        out = None
    if out:
        try:
            sys.stdout.write(out + "\n")
            sys.stdout.flush()
        except Exception:
            pass
    return 0  # never block; stdout carries at most one systemMessage JSON object


# --------------------------------------------------------------------------- report

def iter_ledger():
    try:
        with open(ledger_path(), encoding="utf-8") as f:
            for line in f:
                try:
                    yield json.loads(line)
                except ValueError:
                    continue
    except FileNotFoundError:
        return


def fmt_int(n: int) -> str:
    return f"{n:,}"


def cmd_report(argv) -> int:
    ap = argparse.ArgumentParser(prog="finops.py report")
    ap.add_argument("--session")
    ap.add_argument("--since", help="YYYY-MM-DD (UTC)")
    ap.add_argument("--by", default="skill", choices=["skill", "session", "day", "model", "tool", "invocation"])
    a = ap.parse_args(argv)

    groups: dict = {}
    tools: dict = {}
    invs: dict = {}   # invocation_id -> latest skill_summary (cumulative)

    def g(key):
        return groups.setdefault(key, {"prompts": 0, "messages": 0, "unpriced": 0, "cost": 0.0,
                                       "tokens": {k: 0 for k in TOKEN_KEYS}})

    for e in iter_ledger():
        if a.session and not str(e.get("session_id", "")).startswith(a.session):
            continue
        if a.since and str(e.get("ts", ""))[:10] < a.since:
            continue
        day, sid = str(e.get("ts", ""))[:10], str(e.get("session_id", ""))
        if e.get("event") == "prompt":
            key = {"skill": e.get("active_skill") or "(none)", "session": sid, "day": day}.get(a.by)
            if key is not None:
                g(key)["prompts"] += 1
        elif e.get("event") == "skill_summary":
            invs[e.get("invocation_id")] = e
        elif e.get("event") == "usage":
            for r in e.get("rows", []):
                key = {"skill": r.get("skill"), "session": sid, "day": day,
                       "model": r.get("pricing_key") or r.get("model")}.get(a.by)
                if key is None:
                    continue
                x = g(key)
                x["messages"] += r.get("messages", 0)
                x["unpriced"] += r.get("unpriced_messages", 0)
                x["cost"] += r.get("cost_usd") or 0.0
                for k in TOKEN_KEYS:
                    x["tokens"][k] += r.get("tokens", {}).get(k, 0)
            for sk, d in (e.get("tool_calls") or {}).items():
                for nm, c in d.items():
                    tools[(sk, nm)] = tools.get((sk, nm), 0) + c

    if a.by == "invocation":
        print_invocations(invs)
        return 0

    if a.by == "tool":
        print(f"{'skill':<28} {'tool':<44} {'calls':>7}")
        print("-" * 81)
        for (sk, nm), c in sorted(tools.items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"{sk[:28]:<28} {nm[:44]:<44} {c:>7}")
        return 0

    hdr = (f"{a.by:<40} {'prompts':>7} {'msgs':>6} {'input':>11} {'output':>11} "
           f"{'cache_w5m':>12} {'cache_w1h':>12} {'cache_read':>13} {'cost_usd':>10}")
    print(hdr)
    print("-" * len(hdr))
    tot = {"prompts": 0, "messages": 0, "unpriced": 0, "cost": 0.0,
           "tokens": {k: 0 for k in TOKEN_KEYS}}
    for key, x in sorted(groups.items(), key=lambda kv: -kv[1]["cost"]):
        t = x["tokens"]
        flag = " *" if x["unpriced"] else ""
        print(f"{str(key)[:40]:<40} {x['prompts']:>7} {x['messages']:>6} {fmt_int(t['input']):>11} "
              f"{fmt_int(t['output']):>11} {fmt_int(t['cache_write_5m']):>12} "
              f"{fmt_int(t['cache_write_1h']):>12} {fmt_int(t['cache_read']):>13} "
              f"{x['cost']:>10.4f}{flag}")
        tot["prompts"] += x["prompts"]; tot["messages"] += x["messages"]
        tot["unpriced"] += x["unpriced"]; tot["cost"] += x["cost"]
        for k in TOKEN_KEYS:
            tot["tokens"][k] += t[k]
    t = tot["tokens"]
    print("-" * len(hdr))
    print(f"{'TOTAL':<40} {tot['prompts']:>7} {tot['messages']:>6} {fmt_int(t['input']):>11} "
          f"{fmt_int(t['output']):>11} {fmt_int(t['cache_write_5m']):>12} "
          f"{fmt_int(t['cache_write_1h']):>12} {fmt_int(t['cache_read']):>13} {tot['cost']:>10.4f}")
    if a.by == "model":
        print("(prompts are not attributable to a model; see --by skill/session/day)")
    if tot["unpriced"]:
        print(f"* {tot['unpriced']} message(s) had no price (unknown model or unpriced mode); "
              "their tokens are counted, their cost is not.")
    if a.by == "skill" and invs:
        print()
        print_invocations(invs)
    print("Cost = Anthropic API list-price estimate from hooks/finops/pricing.json, not an invoice.")
    print("On a Claude subscription (Pro/Max login) you pay no per-token money: the token columns show how much")
    print("of the plan allowance was used. With an API key, cost_usd is roughly what you pay.")
    return 0


def print_invocations(invs: dict) -> None:
    hdr = (f"{'skill invocation':<30} {'started (UTC)':<20} {'dur_s':>7} {'status':<8} {'msgs':>5} "
           f"{'input':>9} {'output':>9} {'cache_w':>10} {'cache_r':>12} {'harness':>7} {'cost_usd':>9}")
    print(hdr)
    print("-" * len(hdr))
    for e in sorted(invs.values(), key=lambda e: str(e.get("started_at") or "")):
        t = e.get("tokens", {})
        dur = e.get("duration_s")
        print(f"{str(e.get('skill'))[:30]:<30} {str(e.get('started_at') or '')[:19]:<20} "
              f"{(f'{dur:.0f}' if dur is not None else '-'):>7} {('done' if e.get('status') == 'done' else 'open'):<8} "
              f"{e.get('messages', 0):>5} {fmt_int(t.get('input', 0)):>9} {fmt_int(t.get('output', 0)):>9} "
              f"{fmt_int(t.get('cache_write_5m', 0) + t.get('cache_write_1h', 0)):>10} "
              f"{fmt_int(t.get('cache_read', 0)):>12} {e.get('harness_tool_calls', 0):>7} "
              f"{e.get('cost_usd', 0):>9.4f}{' *' if e.get('unpriced_messages') else ''}")


def main(argv) -> int:
    if not argv or argv[0] == "hook":
        return cmd_hook()
    if argv[0] == "report":
        return cmd_report(argv[1:])
    sys.stderr.write(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
