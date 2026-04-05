#!/usr/bin/env python3
"""
kora_pulse_patch.py — one-time patch to add /pulse command to kora.py.

Run on VPS: python3 kora_pulse_patch.py
Creates a .bak before modifying anything.
"""
import shutil
import sys
from datetime import datetime
from pathlib import Path

KORA_PY = Path(__file__).parent / "kora.py"

# ── what we're inserting ──────────────────────────────────────────────────────

# Into handle_cli(), before "return False"
HANDLE_CLI_INSERT = """
    if arg == "pulse":
        from kora_pulse import run_pulse
        print(run_pulse(verbose=True))
        return True

"""

# Into main() interactive loop, after the selfcheck block
INTERACTIVE_INSERT = """
        if ul in ("pulse", "/pulse"):
            from kora_pulse import run_pulse
            print("\\nKORA: Running pulse...")
            print("\\nKORA:\\n" + run_pulse(verbose=False))
            continue

"""

# ── anchors ───────────────────────────────────────────────────────────────────

# handle_cli() anchor — insert just before the final return False
HANDLE_CLI_ANCHOR = "    return False\n"

# Interactive loop anchor — insert after the selfcheck block
INTERACTIVE_ANCHOR = '        if ul == "selfcheck":\n            print("\\nKORA:\\n" + selfcheck())\n            continue\n'

# ── patch ─────────────────────────────────────────────────────────────────────

def patch():
    if not KORA_PY.exists():
        print(f"[patch] ERROR: {KORA_PY} not found")
        sys.exit(1)

    src = KORA_PY.read_text(encoding="utf-8")

    # Guard: already patched?
    if "kora_pulse" in src:
        print("[patch] kora.py already contains kora_pulse reference — nothing to do.")
        sys.exit(0)

    # Validate anchors exist
    if HANDLE_CLI_ANCHOR not in src:
        print("[patch] ERROR: handle_cli anchor not found — kora.py may have changed.")
        sys.exit(1)

    if INTERACTIVE_ANCHOR not in src:
        print("[patch] ERROR: interactive loop anchor not found — kora.py may have changed.")
        sys.exit(1)

    # Snapshot
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = KORA_PY.with_name(f"kora.py.bak_pre_pulse_{ts}")
    shutil.copy2(KORA_PY, bak)
    print(f"[patch] snapshot -> {bak.name}")

    # Patch 1: handle_cli() — insert before "return False"
    # Replace only the LAST occurrence (handle_cli's return False)
    last_idx = src.rfind(HANDLE_CLI_ANCHOR)
    src = src[:last_idx] + HANDLE_CLI_INSERT + src[last_idx:]
    print("[patch] handle_cli() patched")

    # Patch 2: interactive loop — insert after selfcheck block
    idx = src.find(INTERACTIVE_ANCHOR)
    after = idx + len(INTERACTIVE_ANCHOR)
    src = src[:after] + INTERACTIVE_INSERT + src[after:]
    print("[patch] interactive loop patched")

    # Write
    KORA_PY.write_text(src, encoding="utf-8")
    print(f"[patch] kora.py updated")
    print("[patch] done. Test with: python3 kora.py pulse")


if __name__ == "__main__":
    patch()
