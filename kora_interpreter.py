import re

def interpret(text):
    raw = text.strip()
    t = raw.lower()

    # ---- STATUS ----
    if re.match(r'^(?:kora\s+)?status$', t):
        return {
            "mode": "action",
            "intent": "get_system_status",
            "args": {},
            "confidence": 0.99
        }

    # ---- LIST FILES ----
    m = re.match(r'^(?:kora\s+)?(?:list|show)\s+(?:files|folder|dir|directory)(?:\s+in\s+(.+))?$', t)
    if m:
        path = m.group(1) or "."
        return {
            "mode": "action",
            "intent": "list_files",
            "args": {"path": path},
            "confidence": 0.95
        }

    # ---- READ FILE ----
    m = re.match(r'^(?:kora\s+)?read\s+file\s+(.+)$', raw, re.IGNORECASE)
    if m:
        return {
            "mode": "action",
            "intent": "read_file",
            "args": {"path": m.group(1)},
            "confidence": 0.94
        }

    # ---- RUN SHELL ----
    m = re.match(r'^(?:kora\s+)?(?:run|execute)\s+(.+)$', raw, re.IGNORECASE)
    if m:
        return {
            "mode": "action",
            "intent": "run_shell",
            "args": {"command": m.group(1)},
            "confidence": 0.90
        }

    # ---- WRITE FILE ----
    m = re.match(r'^(?:kora\s+)?write\s+(?:file\s+)?(.+?)\s+(?:with|containing)\s+(.+)$', raw, re.IGNORECASE)
    if m:
        return {
            "mode": "action",
            "intent": "write_file",
            "args": {
                "path": m.group(1).strip(),
                "content": m.group(2)
            },
            "confidence": 0.88
        }

    # ---- PATCH FILE ----
    m = re.match(r'^(?:kora\s+)?update\s+(.+?)\s+(?:to|with)\s+(.+)$', raw, re.IGNORECASE)
    if m:
        return {
            "mode": "action",
            "intent": "patch_file",
            "args": {
                "path": m.group(1).strip(),
                "instruction": m.group(2).strip()
            },
            "confidence": 0.85
        }

    return {
        "mode": "chat",
        "intent": "unknown",
        "args": {"text": text},
        "confidence": 0.50
    }
