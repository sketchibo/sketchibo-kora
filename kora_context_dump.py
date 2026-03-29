#!/usr/bin/env python3
"""
kora_context_dump.py — VPS-side context exporter for Claude session-start ingestion.

Prints startup_context + recent facts + guidance so Claude can ingest
Kora's current state at the top of a new session.

Usage:
  python3 kora_context_dump.py
  python3 kora_context_dump.py --n 50   (last N facts, default 30)
"""
import json
import sys
from pathlib import Path

BASE = Path.home() / "kora"
CTX_FILE = BASE / "memory" / "startup_context.json"
FACTS_FILE = BASE / "memory" / "facts.jsonl"
GUIDANCE_FILE = BASE / "memory" / "guidance.md"
TRAJECTORY_FILE = BASE / "memory" / "trajectory.json"

n_facts = 30
if "--n" in sys.argv:
    try:
        n_facts = int(sys.argv[sys.argv.index("--n") + 1])
    except (IndexError, ValueError):
        pass

SEP = "=" * 60

print(SEP)
print("KORA CONTEXT DUMP")
print(SEP)

# --- startup context ---
print("\n--- STARTUP CONTEXT ---")
try:
    ctx = json.loads(CTX_FILE.read_text(encoding="utf-8"))
    u = ctx.get("user") or {}
    p = ctx.get("project") or {}
    principles = ctx.get("pinned_principles") or []
    goals = ctx.get("active_goals") or []
    tasks = ctx.get("open_tasks") or []
    last = ctx.get("last_session_summary") or ""

    print(f"User:     {u.get('name')} ({u.get('role')})")
    print(f"Project:  {p.get('name')} — {p.get('mission', '')}")
    if principles:
        print("Principles: " + "; ".join(principles))
    if goals:
        print("Goals:")
        for g in goals:
            print(f"  - {g}")
    if tasks:
        print("Open tasks:")
        for t in tasks:
            print(f"  - {t}")
    if last:
        print(f"Last session: {last}")
except FileNotFoundError:
    print("[startup_context.json not found]")
except Exception as e:
    print(f"[startup_context error: {e}]")

# --- trajectory ---
print("\n--- TRAJECTORY ---")
try:
    traj = json.loads(TRAJECTORY_FILE.read_text(encoding="utf-8"))
    arc = traj.get("current_arc") or ""
    if arc:
        print(f"Current arc: {arc}")
    recent = traj.get("recent_moves") or []
    if recent:
        print("Recent moves: " + "; ".join(str(x) for x in recent[-5:]))
except FileNotFoundError:
    print("[no trajectory.json]")
except Exception as e:
    print(f"[trajectory error: {e}]")

# --- recent facts ---
print(f"\n--- RECENT FACTS (last {n_facts}) ---")
try:
    lines = FACTS_FILE.read_text(encoding="utf-8").strip().splitlines()
    for line in lines[-n_facts:]:
        try:
            row = json.loads(line)
            ts = (row.get("ts") or "")[:19]
            src = row.get("source") or row.get("kind") or "?"
            txt = row.get("text") or str(row)
            print(f"[{ts}] ({src}) {txt[:200]}")
        except Exception:
            print(f"  {line[:200]}")
except FileNotFoundError:
    print("[facts.jsonl not found]")
except Exception as e:
    print(f"[facts error: {e}]")

# --- guidance ---
print("\n--- GUIDANCE ---")
try:
    guidance = GUIDANCE_FILE.read_text(encoding="utf-8").strip()
    print(guidance[:1500])
    if len(guidance) > 1500:
        print("  [... truncated]")
except FileNotFoundError:
    print("[no guidance.md]")
except Exception as e:
    print(f"[guidance error: {e}]")

print(f"\n{SEP}")
print("END KORA CONTEXT DUMP")
print(SEP)
