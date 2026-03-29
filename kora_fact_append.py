#!/usr/bin/env python3
"""
kora_fact_append.py — VPS-side stdin receiver, appends to memory/facts.jsonl.

Usage:
  echo "some note" | python3 kora_fact_append.py
  echo "some note" | python3 kora_fact_append.py claude_handoff
"""
import json
import sys
from datetime import datetime
from pathlib import Path

FACTS = Path.home() / "kora" / "memory" / "facts.jsonl"
source = sys.argv[1] if len(sys.argv) > 1 else "claude_note"

text = sys.stdin.read().strip()
if not text:
    sys.exit(0)

FACTS.parent.mkdir(parents=True, exist_ok=True)
row = {
    "ts": datetime.now().isoformat(),
    "kind": "fact",
    "source": source,
    "text": text,
}
with FACTS.open("a", encoding="utf-8") as f:
    f.write(json.dumps(row, ensure_ascii=False) + "\n")

print(f"[kora] saved ({source}): {text[:80]}", flush=True)
