from typing import Dict, Any

SHELL_STARTS = (
    "cd ", "ls", "pwd", "cat ", "grep ", "sed ", "awk ", "find ", "tail ", "head ",
    "python ", "python3 ", "curl ", "scp ", "ssh ", "nano ", "vim ", "cp ", "mv ",
    "rm ", "mkdir ", "touch ", "echo ", "wc ", "nl ", "jq ", "time "
)

DEBUG_TERMS = {
    "error", "broken", "broke", "debug", "traceback", "timeout", "timed out",
    "won't", "wont", "can't", "cannot", "failed", "failing", "fix", "issue",
    "selfcheck", "snapshot", "hooked", "hook", "compile", "syntax"
}

VOICE_TERMS = {
    "voice", "speak", "speaking", "tts", "text to speech", "piper", "nemo",
    "nvidia", "mnemonic", "personaplex", "persona plex", "sound like",
    "how would you like to speak", "your voice"
}

META_TERMS = {
    "kora", "lyra", "off", "wrong", "weird", "helpful", "hooked up",
    "what are you doing", "how are you feeling", "self check"
}

BANTER_TERMS = {
    "lol", "lmao", "haha", "heh", "hehe", "from the back", "new angle"
}

def _term_hits(text: str, terms) -> int:
    lower = text.lower()
    return sum(1 for t in terms if t in lower)

def _shell_score(text: str) -> int:
    lower = text.lower().strip()
    score = 0

    if any(lower.startswith(x) for x in SHELL_STARTS):
        score += 3
    if "kayle@vultr:" in lower or "~$" in lower or "traceback (most recent call last)" in lower:
        score += 3
    if "|| exit 1" in lower or "&& echo" in lower or "| sed -n" in lower or ">/dev/null" in lower:
        score += 2
    if 'file "' in lower and "line " in lower:
        score += 2

    return score

def classify_input(user_text: str) -> Dict[str, Any]:
    shell_score = _shell_score(user_text)
    debug_score = _term_hits(user_text, DEBUG_TERMS)
    voice_score = _term_hits(user_text, VOICE_TERMS)
    meta_score = _term_hits(user_text, META_TERMS)
    banter_score = _term_hits(user_text, BANTER_TERMS)

    mode = "general_chat"
    notes = []

    if shell_score >= 3:
        mode = "shell_blob"
        notes.append("Treat this as shell/log text, not ordinary conversation.")
    elif voice_score >= 2 and voice_score >= debug_score:
        mode = "voice_identity"
        notes.append("Stay at the level of voice, presence, and identity first.")
    elif debug_score >= 2:
        mode = "task_debug"
        notes.append("Prioritize concrete troubleshooting.")
    elif meta_score >= 1 and voice_score == 0:
        mode = "meta_system_talk"
        notes.append("This is about KORA/Lyra/system behavior.")
    elif banter_score >= 1:
        mode = "rapport_banter"
        notes.append("A light playful read is plausible.")

    scores = {
        "shell_blob": shell_score,
        "task_debug": debug_score,
        "voice_identity": voice_score,
        "meta_system_talk": meta_score,
        "rapport_banter": banter_score,
    }
    raw = max(scores.get(mode, 1), 1)
    confidence = min(0.95, 0.35 + raw * 0.12)

    return {
        "mode": mode,
        "confidence": round(confidence, 3),
        "scores": scores,
        "notes": notes,
    }
