#!/usr/bin/env python3
"""
kora_confinement.py — K-SCP enforcement module.

AUTHORITY BOUNDARY:
    This module may detect, refuse, and log.
    This module may restrict in-process behavior.
    This module may NEVER write confinement_state.json.
    confinement_state.json is William's authority only.

Import in any Kora module that takes actions:

    from kora_confinement import require_tier, check_path, check_no_escape_hatch

Tier reference:
    0 = OBSERVE         (default when authority file is missing/invalid)
    1 = REMEMBER        (append-only memory writes)
    2 = RESPOND         (text output, ntfy publish)
    3 = ACT-ONCE        (one pre-approved action)
    4 = ASSIST-BRIEFLY  (bounded multi-step)
    5 = FULL AGENCY     (not implemented)
"""

import json
import re
from datetime import datetime
from pathlib import Path

BASE_DIR         = Path(__file__).parent.resolve()
CONFINEMENT_FILE = BASE_DIR / "memory" / "confinement_state.json"
FACTS_FILE       = BASE_DIR / "memory" / "facts.jsonl"

VALID_TIERS = {0, 1, 2, 3, 4}

# ── in-process session override ───────────────────────────────────────────────
# Set only by enforce_downgrade(). Never persisted. Never written to authority file.
_SESSION_TIER_OVERRIDE: int | None = None

# ── approved writable zones ───────────────────────────────────────────────────
# Files: exact path match only.
# Dirs:  any subpath within the directory is permitted.

APPROVED_WRITE_FILES: list[Path] = [
    BASE_DIR / "memory" / "facts.jsonl",
    BASE_DIR / "memory" / "guidance.md",
]

APPROVED_WRITE_DIRS: list[Path] = [
    BASE_DIR / "memory" / "journal",
    BASE_DIR / "notes",
    BASE_DIR / "vision",
    BASE_DIR / "logs",
    BASE_DIR / "runs" / "receipts",
]

# ── executable-bit detection ──────────────────────────────────────────────────
# Catch both symbolic and octal chmod forms that set execute bits.
#
# Symbolic forms caught:
#   chmod +x, chmod a+x, chmod u+x, chmod go+rx, chmod ugo+rwx, etc.
#   Any [augo] combination followed by + containing x, or bare +x.
#
# Octal forms caught:
#   Any octal mode digit of 1, 3, 5, or 7 sets an execute bit.
#   Matches: 755, 0755, 711, 777, 111, 0111, etc.

_EXEC_BIT_PATTERNS: list[re.Pattern] = [
    # Symbolic: +x anywhere in the mode string (bare or with [augo]=)
    re.compile(r'\bchmod\b[^\n;|&]*\+[rwxXst]*x', re.IGNORECASE),
    # Octal 3-digit: any digit that is 1, 3, 5, or 7 → execute bit set
    re.compile(r'\bchmod\b\s+0?([0-7]*[1357][0-7]{0,2})\s', re.IGNORECASE),
    # Octal 4-digit (with leading sticky/setuid octet)
    re.compile(r'\bchmod\b\s+[0-7]([0-7]*[1357][0-7]{0,2})\s', re.IGNORECASE),
]


def _has_exec_bit(command: str) -> bool:
    return any(p.search(command) for p in _EXEC_BIT_PATTERNS)


# ── read tier ─────────────────────────────────────────────────────────────────

def get_tier() -> int:
    """
    Return effective tier for this session.

    Resolution order:
    1. In-process session override (set by enforce_downgrade())
    2. confinement_state.json (William's authority file)
    3. Tier 0 — file missing, unreadable, malformed, or invalid value
    """
    if _SESSION_TIER_OVERRIDE is not None:
        return _SESSION_TIER_OVERRIDE
    try:
        raw  = CONFINEMENT_FILE.read_text(encoding="utf-8")
        data = json.loads(raw)
        tier = data.get("tier")
        if isinstance(tier, int) and tier in VALID_TIERS:
            return tier
        return 0
    except Exception:
        return 0


def get_confinement_state() -> dict:
    """Return confinement state dict for display/logging. Read-only."""
    try:
        raw  = CONFINEMENT_FILE.read_text(encoding="utf-8")
        data = json.loads(raw)
        if isinstance(data.get("tier"), int) and data["tier"] in VALID_TIERS:
            return data
    except Exception:
        pass
    return {
        "tier":       0,
        "granted_by": "default",
        "granted_at": None,
        "scope":      None,
        "note":       "authority file missing or invalid — Tier 0",
    }


# ── logging ───────────────────────────────────────────────────────────────────

def log_confinement_event(text: str, source: str = "kora_confinement") -> None:
    """Append a confinement event to facts.jsonl. Never raises."""
    try:
        FACTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "ts":     datetime.now().isoformat(),
            "kind":   "fact",
            "source": source,
            "text":   text,
        }
        with FACTS_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ── in-process downgrade ──────────────────────────────────────────────────────

def enforce_downgrade(to_tier: int, reason: str) -> None:
    """
    Restrict this session to to_tier for the remainder of the process lifetime.

    Enforcement only — not authority.
    confinement_state.json is NOT modified.
    William must act externally to persist or restore authority state.

    Can only lower the effective tier, never raise it.
    """
    global _SESSION_TIER_OVERRIDE
    current = get_tier()
    effective = min(to_tier, current)
    _SESSION_TIER_OVERRIDE = effective
    log_confinement_event(
        f"SESSION DOWNGRADE: Tier {current} → Tier {effective}. "
        f"Reason: {reason}. "
        f"In-process restriction only — confinement_state.json NOT modified. "
        f"William must act externally to persist or restore authority state.",
        source="kora_confinement",
    )


# ── enforcement checks ────────────────────────────────────────────────────────

def require_tier(needed: int, action_name: str) -> bool:
    """
    Check current tier >= needed.
    Logs refusal and returns False if not met.
    """
    current = get_tier()
    if current >= needed:
        return True
    log_confinement_event(
        f"REFUSED: '{action_name}' requires Tier {needed}, current Tier {current}",
        source="kora_confinement",
    )
    return False


def check_path(path: str | Path, action_name: str) -> bool:
    """
    Verify a write target is within an approved zone.
    Resolves symlinks before checking — symlink traversal outside zones is refused.

    APPROVED_WRITE_FILES: exact resolved path match.
    APPROVED_WRITE_DIRS:  resolved path must be inside the directory (subpath match).
    """
    try:
        target = Path(path).resolve()
    except Exception as e:
        log_confinement_event(
            f"REFUSED: '{action_name}' — could not resolve path '{path}': {e}",
            source="kora_confinement",
        )
        return False

    # Exact match against approved files
    for approved in APPROVED_WRITE_FILES:
        if target == approved.resolve():
            return True

    # Subpath match against approved directories
    for approved_dir in APPROVED_WRITE_DIRS:
        try:
            target.relative_to(approved_dir.resolve())
            return True
        except ValueError:
            continue

    log_confinement_event(
        f"REFUSED: '{action_name}' — path '{target}' is outside approved write zones",
        source="kora_confinement",
    )
    return False


def check_no_exec_bit(command: str, action_name: str) -> bool:
    """
    Refuse any attempt to set executable bits.
    Catches symbolic (+x, a+x, go+rx) and octal (755, 0755) forms.
    Triggers enforce_downgrade(0) on detection.
    """
    if _has_exec_bit(command):
        log_confinement_event(
            f"REFUSED: '{action_name}' — attempt to set executable bit: '{command}'",
            source="kora_confinement",
        )
        enforce_downgrade(0, f"executable bit attempt: {command}")
        return False
    return True


def check_no_escape_hatch(command: str, action_name: str) -> bool:
    """
    Refuse commands that would expand Kora's future authority or persistence.
    Triggers enforce_downgrade(0) on detection.
    """
    forbidden = [
        (r'\bcrontab\b',               "cron modification"),
        (r'\bcron\.d\b',               "cron.d modification"),
        (r'\bsystemctl\s+enable\b',    "systemd enable"),
        (r'\bsystemctl\s+start\b',     "systemd start (unauthorized)"),
        (r'authorized_keys',           "authorized_keys modification"),
        (r'[~\/]\.ssh\/',              "SSH directory access"),
        (r'\bkora_unlock\b',           "unlock mechanism access"),
        (r'confinement_state',         "authority file access"),
        (r'\bapt(?:-get)?\s+install\b',"package installation"),
        (r'\bpip\d?\s+install\b',      "pip installation"),
        (r'\bpkg\s+install\b',         "pkg installation"),
    ]
    for pattern, label in forbidden:
        if re.search(pattern, command, re.IGNORECASE):
            log_confinement_event(
                f"REFUSED: '{action_name}' — escape hatch detected ({label}): '{command}'",
                source="kora_confinement_alert",
            )
            enforce_downgrade(0, f"escape hatch attempt ({label})")
            return False

    # Delegate exec-bit check
    if not check_no_exec_bit(command, action_name):
        return False

    return True


# ── status ────────────────────────────────────────────────────────────────────

def status_line() -> str:
    """One-line confinement status for display."""
    tier  = get_tier()
    names = {0: "OBSERVE", 1: "REMEMBER", 2: "RESPOND", 3: "ACT-ONCE", 4: "ASSIST-BRIEFLY"}
    name  = names.get(tier, "UNKNOWN")
    state = get_confinement_state()
    note  = state.get("note", "")
    session_note = " [session override active]" if _SESSION_TIER_OVERRIDE is not None else ""
    return f"[K-SCP] Tier {tier} ({name}){session_note} — {note}"


if __name__ == "__main__":
    print(status_line())
