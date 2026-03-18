import re
from typing import Dict, Any


def interpret(user_input: str) -> Dict[str, Any]:
    text = user_input.strip()
    lower = text.lower()

    if lower in {"status", "kora status", "system status", "sys status"}:
        return {
            "mode": "action",
            "intent": "get_system_status",
            "args": {},
            "confidence": 0.99,
        }

    if any(p in lower for p in ["memory usage", "ram usage", "show memory", "check memory"]):
        return {
            "mode": "action",
            "intent": "run_shell",
            "args": {"command": "free -h"},
            "confidence": 0.95,
        }

    if any(p in lower for p in ["disk usage", "check disk", "show disk", "df -h"]):
        return {
            "mode": "action",
            "intent": "run_shell",
            "args": {"command": "df -h"},
            "confidence": 0.95,
        }

    if "restart ollama" in lower:
        return {
            "mode": "action",
            "intent": "run_shell",
            "args": {"command": "sudo systemctl restart ollama"},
            "confidence": 0.92,
        }

    if any(p in lower for p in ["ollama models", "show models", "list models"]):
        return {
            "mode": "action",
            "intent": "run_shell",
            "args": {"command": "ollama list"},
            "confidence": 0.94,
        }

    if any(p in lower for p in ["show uptime", "uptime", "check uptime"]):
        return {
            "mode": "action",
            "intent": "run_shell",
            "args": {"command": "uptime"},
            "confidence": 0.94,
        }

    if any(p in lower for p in ["check load", "show load", "cpu load"]):
        return {
            "mode": "action",
            "intent": "run_shell",
            "args": {"command": "uptime"},
            "confidence": 0.93,
        }

    if any(p in lower for p in ["tail ollama log", "show ollama log", "ollama log"]):
        return {
            "mode": "action",
            "intent": "run_shell",
            "args": {"command": "sudo journalctl -u ollama -n 50 --no-pager"},
            "confidence": 0.93,
        }

    if any(p in lower for p in ["latest snapshot", "show last snapshot", "show latest snapshot"]):
        return {
            "mode": "action",
            "intent": "run_shell",
            "args": {"command": "ls -1t snapshots/*.json 2>/dev/null | head -n 1"},
            "confidence": 0.91,
        }

    m = re.match(r"^(?:kora\s+it\s+)?run\s+(.+)$", text, re.IGNORECASE)
    if m:
        return {
            "mode": "action",
            "intent": "run_shell",
            "args": {"command": m.group(1).strip()},
            "confidence": 0.90,
        }

    return {
        "mode": "chat",
        "intent": "chat",
        "args": {"text": text},
        "confidence": 0.40,
    }
