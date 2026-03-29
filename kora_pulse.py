#!/usr/bin/env python3
"""
kora_pulse.py — Autonomy Phase 1.

KORA inspects her current state, identifies the single most important
unresolved issue, and outputs one recommended next action with reasoning.
Logs the recommendation to memory/facts.jsonl.

Standalone:  python3 kora_pulse.py
From kora:   python3 kora.py pulse
Import:      from kora_pulse import run_pulse
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.resolve()
os.chdir(BASE_DIR)
load_dotenv(dotenv_path=BASE_DIR / ".env")

FACTS_PATH     = BASE_DIR / "memory" / "facts.jsonl"
CTX_PATH       = BASE_DIR / "memory" / "startup_context.json"
TRAJECTORY_PATH = BASE_DIR / "memory" / "trajectory.json"
GUIDANCE_PATH  = BASE_DIR / "memory" / "guidance.md"

OLLAMA_URL   = "http://127.0.0.1:11434/api/generate"
VENICE_URL   = "https://api.venice.ai/api/v1/chat/completions"
VENICE_MODEL = "venice-uncensored"
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL   = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)


# ── context assembly ──────────────────────────────────────────────────────────

def _read(path: Path, default: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return default


def _recent_facts(n: int = 15) -> str:
    try:
        lines = FACTS_PATH.read_text(encoding="utf-8").strip().splitlines()
        rows = []
        for line in lines[-n:]:
            try:
                obj = json.loads(line)
                ts  = (obj.get("ts") or "")[:19]
                src = obj.get("source") or obj.get("kind") or "?"
                txt = obj.get("text") or str(obj)
                rows.append(f"[{ts}] ({src}) {txt[:200]}")
            except Exception:
                rows.append(line[:200])
        return "\n".join(rows)
    except Exception:
        return "[no facts]"


def _startup_summary() -> str:
    try:
        ctx = json.loads(CTX_PATH.read_text(encoding="utf-8"))
        u      = (ctx.get("user") or {}).get("name", "William")
        goals  = ctx.get("active_goals") or []
        tasks  = ctx.get("open_tasks") or []
        last   = ctx.get("last_session_summary") or ""
        lines  = [f"User: {u}"]
        if goals:
            lines.append("Active goals: " + "; ".join(goals))
        if tasks:
            lines.append("Open tasks: " + "; ".join(tasks))
        if last:
            lines.append(f"Last session: {last}")
        return "\n".join(lines)
    except Exception:
        return "[no startup_context]"


def _trajectory_summary() -> str:
    try:
        traj = json.loads(TRAJECTORY_PATH.read_text(encoding="utf-8"))
        arc  = traj.get("current_arc") or ""
        return f"Current arc: {arc}" if arc else "[no arc]"
    except Exception:
        return "[no trajectory]"


def _build_pulse_prompt() -> str:
    ctx      = _startup_summary()
    traj     = _trajectory_summary()
    facts    = _recent_facts(15)
    guidance = _read(GUIDANCE_PATH)[:800]

    return f"""You are KORA — a local-first, continuity-aware AI agent.
You are performing an autonomy pulse: a brief, grounded state inspection.

DO NOT repeat back the context. DO NOT give generic advice. Be specific to what is actually in front of you.

== STARTUP CONTEXT ==
{ctx}

== TRAJECTORY ==
{traj}

== RECENT FACTS ==
{facts}

== GUIDANCE ==
{guidance}

== TASK ==
Based on everything above:
1. Identify the single most important unresolved issue right now.
2. Recommend one concrete next action.
3. Give brief reasoning (1-2 sentences).

Respond in exactly this format — no extra text before or after:

UNRESOLVED: <one clear sentence identifying the gap>
ACTION: <one concrete, doable next step>
REASONING: <why this action addresses the gap>"""


# ── backends ──────────────────────────────────────────────────────────────────

def _venice(prompt: str) -> str | None:
    key = os.getenv("VENICE_API_KEY", "").strip()
    if not key:
        return None
    payload = {
        "model": VENICE_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }
    for auth in (
        {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        {"x-api-key": key, "Content-Type": "application/json"},
    ):
        try:
            r = requests.post(VENICE_URL, headers=auth, json=payload, timeout=30)
            if r.status_code in (401, 403):
                continue
            r.raise_for_status()
            choices = r.json().get("choices") or []
            if choices:
                content = (choices[0].get("message") or {}).get("content", "")
                if content.strip():
                    return content.strip()
        except Exception:
            continue
    return None


def _gemini(prompt: str) -> str | None:
    key = (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "").strip()
    if not key:
        return None
    url = f"{GEMINI_URL}?key={key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        r = requests.post(url, json=payload, timeout=30)
        if r.status_code in (401, 403):
            return None
        r.raise_for_status()
        candidates = r.json().get("candidates") or []
        if candidates:
            parts = ((candidates[0].get("content") or {}).get("parts") or [])
            text = "".join(p.get("text", "") for p in parts if isinstance(p, dict)).strip()
            return text or None
    except Exception:
        pass
    return None


def _ollama(prompt: str) -> str | None:
    try:
        r = requests.post(
            OLLAMA_URL,
            json={"model": "qwen2.5:7b", "prompt": prompt, "stream": False},
            timeout=90,
        )
        r.raise_for_status()
        text = r.json().get("response", "").strip()
        return text or None
    except Exception:
        return None


def _best_response(prompt: str) -> str:
    for fn, name in ((_venice, "venice"), (_gemini, "gemini"), (_ollama, "ollama")):
        result = fn(prompt)
        if result:
            return result
    return "[PULSE ERROR: all backends unreachable]"


# ── logging ───────────────────────────────────────────────────────────────────

def _log_pulse(text: str) -> None:
    FACTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "ts":     datetime.now().isoformat(),
        "kind":   "fact",
        "source": "kora_pulse",
        "text":   text,
    }
    with FACTS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


# ── public entry point ────────────────────────────────────────────────────────

def run_pulse(verbose: bool = True) -> str:
    """
    Assemble context, call best available backend, log result, return text.
    """
    if verbose:
        print("[pulse] assembling context...", flush=True)

    prompt = _build_pulse_prompt()

    if verbose:
        print("[pulse] querying best backend...", flush=True)

    raw = _best_response(prompt)

    # Normalize: ensure the three fields are present
    output_lines = []
    has_unresolved = "UNRESOLVED:" in raw
    has_action     = "ACTION:" in raw
    has_reasoning  = "REASONING:" in raw

    if has_unresolved and has_action and has_reasoning:
        # Clean response — pass through
        output = raw.strip()
    else:
        # Wrap freeform response
        output = f"UNRESOLVED: [see raw below]\nACTION: Review KORA pulse output\nREASONING: Backend did not follow structured format.\n\nRAW:\n{raw}"

    _log_pulse(output)

    return output


# ── standalone run ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    result = run_pulse(verbose=True)
    print("\n" + "=" * 60)
    print("KORA PULSE")
    print("=" * 60)
    print(result)
    print("=" * 60)
    print("[pulse] logged to memory/facts.jsonl")
