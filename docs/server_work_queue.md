# Server Work Queue

This file is the interim work queue for KORA while higher-reasoning cloud support is unavailable.

## Current posture
Work on the server first. Preserve momentum. Keep KORA local-first and authoritative.

## Immediate priorities
1. Inventory current memory, ledger, and state files on the server.
2. Identify canonical startup context and continuity paths.
3. Confirm current repo state and active bridge docs.
4. Prepare minimal bridge scaffolding for later implementation.

## Commands to run on server
```bash
cd ~/kora || cd ~
pwd
ls -la
find . -maxdepth 3 \( -iname '*memory*' -o -iname '*ledger*' -o -iname '*state*' -o -iname '*snapshot*' -o -iname '*context*' \) | sort
find . -maxdepth 3 -type f \( -name 'kora.py' -o -name 'kora_interpreter.py' -o -name 'kora_tools.py' -o -name '*.jsonl' -o -name '*.md' \) | sort
```

## Files to inspect first
- kora.py
- kora_interpreter.py
- kora_tools.py
- memory/
- logs/
- notes/
- core/identity/
- any startup_context, ledger, facts, or snapshot files
- docs/claude_handoff_for_kora.md

## Goal
By the time Claude is back, KORA should already have:
- exact file inventory
- known continuity surfaces
- known ledger/memory paths
- a stable starting point for the bridge implementation

## North star
Many minds may think through KORA.
Only KORA persists.
