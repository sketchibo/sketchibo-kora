#!/usr/bin/env python3
import os
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def run(cmd):
    try:
        out = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT)
        return out.strip()
    except Exception as e:
        return f"[error running {cmd!r}: {e}]"

def safe_read(path, limit=12000):
    try:
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
        return text[:limit]
    except Exception as e:
        return f"[could not read {path}: {e}]"

def list_tree(root, max_entries=200):
    items = []
    count = 0
    for p in sorted(root.rglob("*")):
        if count >= max_entries:
            items.append("... [truncated]")
            break
        rel = p.relative_to(root)
        items.append(str(rel) + ("/" if p.is_dir() else ""))
        count += 1
    return "\n".join(items)

def main():
    snapshot = {
        "identity": {
            "name": "KORA",
            "project_root": str(ROOT),
            "python_entrypoint_guess": "kora.py",
            "purpose": "Local-first AI orchestration / council system running on a VPS for William"
        },
        "environment": {
            "hostname": run("hostname"),
            "whoami": run("whoami"),
            "pwd": str(ROOT),
            "python_version": run("python3 --version"),
            "uptime": run("uptime"),
        },
        "models": {
            "ollama_list": run("ollama list")
        },
        "files": {
            "root_listing": run(f"cd {ROOT} && ls -lah"),
            "tree_sample": list_tree(ROOT),
        },
        "code_summary": {
            "kora_py_head": safe_read(ROOT / "kora.py", 10000),
            "kora_interpreter_py_head": safe_read(ROOT / "kora_interpreter.py", 8000),
            "kora_tools_py_head": safe_read(ROOT / "kora_tools.py", 8000),
        },
        "self_description_prompt": (
            "Based on this snapshot, describe what KORA is, how it is structured, "
            "what kind of AI architecture it resembles, its strengths, weaknesses, "
            "and what it could evolve into."
        )
    }

    print(json.dumps(snapshot, indent=2))

if __name__ == "__main__":
    main()
