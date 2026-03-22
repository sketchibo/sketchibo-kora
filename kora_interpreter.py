import re
from typing import Dict, Any


SELF_CHECK_COMMAND = r"""bash -lc '
set +e

latest_signal_ts=$(tail -n 1 memory/signals.jsonl 2>/dev/null | python3 -c "import sys,json; s=sys.stdin.read().strip(); print(json.loads(s).get(\"ts\",\"missing\") if s else \"missing\")" 2>/dev/null)
latest_snapshot=$(ls -1t snapshots/*.json 2>/dev/null | head -n 1)

ollama_status="unverified"
if curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  ollama_status="reachable"
fi

echo "SELF-CHECK"
echo "- Checked:"
echo "  - memory/startup_context.json"
echo "  - memory/guidance.md"
echo "  - memory/signals.jsonl"
echo "  - memory/facts.jsonl"
echo "  - snapshots/*.json"
echo "  - Ollama API at http://127.0.0.1:11434/api/tags"

echo "- Verified:"
[ -f memory/startup_context.json ] && echo "  - startup_context.json exists"
[ -f memory/guidance.md ] && echo "  - guidance.md exists"
[ -f memory/signals.jsonl ] && echo "  - signals.jsonl exists"
[ -f memory/facts.jsonl ] && echo "  - facts.jsonl exists"
[ "$latest_signal_ts" != "missing" ] && echo "  - latest signal timestamp: $latest_signal_ts"
[ -n "$latest_snapshot" ] && echo "  - latest snapshot file: $latest_snapshot"
[ "$ollama_status" = "reachable" ] && echo "  - Ollama API reachable"

echo "- Unverified:"
[ ! -f memory/startup_context.json ] && echo "  - startup_context.json missing"
[ ! -f memory/guidance.md ] && echo "  - guidance.md missing"
[ ! -f memory/signals.jsonl ] && echo "  - signals.jsonl missing"
[ ! -f memory/facts.jsonl ] && echo "  - facts.jsonl missing"
[ "$latest_signal_ts" = "missing" ] && echo "  - could not read latest signal timestamp"
[ -z "$latest_snapshot" ] && echo "  - no snapshot file found under snapshots/"
[ "$ollama_status" != "reachable" ] && echo "  - Ollama API not reachable"

echo "- Problems found:"
problems=0
[ ! -f memory/startup_context.json ] && echo "  - missing startup context file" && problems=1
[ ! -f memory/guidance.md ] && echo "  - missing guidance file" && problems=1
[ ! -f memory/signals.jsonl ] && echo "  - missing signals log" && problems=1
[ ! -f memory/facts.jsonl ] && echo "  - missing facts log" && problems=1
[ -z "$latest_snapshot" ] && echo "  - no snapshot found" && problems=1
[ "$ollama_status" != "reachable" ] && echo "  - Ollama is not responding on 127.0.0.1:11434" && problems=1
[ "$problems" -eq 0 ] && echo "  - no hard failures in the checked items"

echo "- Next useful action:"
if [ -z "$latest_snapshot" ]; then
  echo "  - create a fresh snapshot before edits"
elif [ "$ollama_status" != "reachable" ]; then
  echo "  - restore Ollama service before further KORA tests"
else
  echo "  - move self-check into a dedicated action path in kora.py instead of generic chat fallback"
fi
'"""



GROUNDED_STATUS_COMMAND = r"""bash -lc '
set +e

latest_signal_ts=$(tail -n 1 memory/signals.jsonl 2>/dev/null | python3 -c "import sys,json; s=sys.stdin.read().strip(); print(json.loads(s).get(\"ts\",\"missing\") if s else \"missing\")" 2>/dev/null)
latest_snapshot=$(ls -1t snapshots/*.json 2>/dev/null | head -n 1)

ollama_status="unverified"
if curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  ollama_status="reachable"
fi

echo "VERIFIED:"
[ -f memory/startup_context.json ] && echo "- startup_context.json exists"
[ -f memory/guidance.md ] && echo "- guidance.md exists"
[ -f memory/signals.jsonl ] && echo "- signals.jsonl exists"
[ -f memory/facts.jsonl ] && echo "- facts.jsonl exists"
[ "$latest_signal_ts" != "missing" ] && echo "- latest signal timestamp: $latest_signal_ts"
[ -n "$latest_snapshot" ] && echo "- latest snapshot file: $latest_snapshot"
[ "$ollama_status" = "reachable" ] && echo "- Ollama API reachable"

echo
echo "INFERRED:"
[ -f memory/signals.jsonl ] && echo "- memory/signals pipeline has written at least one entry"
[ -n "$latest_snapshot" ] && echo "- snapshot workflow has been used recently"
[ "$ollama_status" = "reachable" ] && echo "- local model backend is available for KORA"

echo
echo "UNKNOWN:"
echo "- whether KORA chat tone will stay distinct across turns without a code-level mode flag"
echo "- whether generic council fallback has been fully bypassed for all status-style prompts"

echo
echo "NEXT MOVE:"
echo "- patch any remaining generic fallback paths if a status question still drifts into chat"
'"""
def interpret(user_input: str) -> Dict[str, Any]:
    text = user_input.strip()
    lower = text.lower()

    if any(p in lower for p in [
        "project state",
        "project-status",
        "project status",
        "self status",
        "self-status",
        "what is my status",
        "what's my status",
        "what is my current kora status",
        "current kora status",
        "kora status",
        "what can you verify",
        "what cannot you verify",
        "what cant you verify",
        "status right now",
    ]):
        return {
            "mode": "action",
            "intent": "run_shell",
            "args": {"command": GROUNDED_STATUS_COMMAND},
            "confidence": 0.98,
        }

    if lower in {"status", "system status", "sys status"}:
        return {
            "mode": "action",
            "intent": "get_system_status",
            "args": {},
            "confidence": 0.99,
        }

    if any(p in lower for p in [
        "self check",
        "self-check",
        "run a self check",
        "run self check",
        "run a self-check",
        "can you run a self check",
        "can you run a self-check",
        "what exactly did you verify",
        "what did you verify",
    ]):
        return {
            "mode": "action",
            "intent": "run_shell",
            "args": {"command": SELF_CHECK_COMMAND},
            "confidence": 0.98,
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
