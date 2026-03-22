import re
from typing import Dict, Any

NEGATIVE = {
    "bad", "broken", "stuck", "annoying", "frustrating", "frustrated", "hate",
    "shit", "mess", "wrecked", "lost", "confused", "wrong", "fail", "failed",
    "pain", "rough", "tired", "exhausted", "burnt", "fried", "cooked"
}

FRUSTRATION = {
    "fuck", "fucking", "wtf", "damn", "bro", "bruh", "ugh", "stupid",
    "ridiculous", "nonsense", "bullshit", "jesus", "christ"
}

OVERWHELM = {
    "overwhelmed", "too much", "can't keep up", "cannot keep up",
    "spiraling", "drowning", "swamped", "buried"
}

HUMOR = {
    "lol", "lmao", "haha", "hehe", "rofl"
}

IRONY_PHRASES = [
    "yeah right",
    "sure buddy",
    "sure jan",
    "great,",
    "great.",
    "awesome,",
    "awesome.",
    "cool,",
    "cool."
]

VULNERABLE = {
    "ashamed", "embarrassed", "hurt", "scared", "afraid", "lonely", "sad",
    "hopeless", "empty", "numb", "lost"
}

PROBLEM = {
    "error", "bug", "issue", "problem", "broke", "broken", "failing", "traceback",
    "won't", "wont", "can't", "cannot", "stuck", "fix", "debug", "patch"
}

SOLVE = {
    "how", "fix", "debug", "patch", "build", "implement", "do", "make", "write"
}

WITNESS = {
    "feel", "feeling", "wish", "wonder", "tired", "exhausted", "done"
}

SHAME_PHRASES = [
    "i'm an idiot",
    "im an idiot",
    "that was stupid of me",
    "i'm stupid",
    "im stupid",
]

def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))

def _tokens(text: str):
    return re.findall(r"[a-z0-9']+", text.lower())

def _count_token_hits(tokens, lexicon) -> int:
    return sum(1 for t in tokens if t in lexicon)

def _count_phrase_hits(lower: str, phrases) -> int:
    return sum(1 for p in phrases if p in lower)

def _round(v: float) -> float:
    return round(float(v), 3)

def estimate_state(user_text: str, person_model: Dict[str, Any] | None = None, rapport: Dict[str, Any] | None = None) -> Dict[str, Any]:
    person_model = person_model or {}
    rapport = rapport or {}

    lower = user_text.lower()
    tokens = _tokens(user_text)
    letters = [c for c in user_text if c.isalpha()]
    caps_ratio = (sum(1 for c in letters if c.isupper()) / len(letters)) if letters else 0.0

    trust = float(rapport.get("trust_level", 0.5))
    playfulness = float(rapport.get("playfulness_budget", 0.4))

    negative_hits = _count_token_hits(tokens, NEGATIVE)
    frustration_hits = _count_token_hits(tokens, FRUSTRATION)
    humor_hits = _count_token_hits(tokens, HUMOR)
    vulnerable_hits = _count_token_hits(tokens, VULNERABLE)
    problem_hits = _count_token_hits(tokens, PROBLEM)
    solve_hits = _count_token_hits(tokens, SOLVE)
    witness_hits = _count_token_hits(tokens, WITNESS)

    irony_hits = _count_phrase_hits(lower, IRONY_PHRASES)
    overwhelm_hits = _count_phrase_hits(lower, OVERWHELM)
    shame_hits = _count_phrase_hits(lower, SHAME_PHRASES)

    exclaim = user_text.count("!")
    question = user_text.count("?")

    intensity = clamp(
        (negative_hits * 0.07)
        + (frustration_hits * 0.11)
        + (overwhelm_hits * 0.16)
        + (exclaim * 0.04)
        + (caps_ratio * 0.25)
    )

    task_friction = clamp(
        (problem_hits * 0.14)
        + (frustration_hits * 0.10)
        + (_count_phrase_hits(lower, ["won't", "can't", "cannot"]) * 0.18)
        + (_count_phrase_hits(lower, ["error", "traceback", "broken"]) * 0.10)
    )

    vulnerability = clamp(
        (vulnerable_hits * 0.18)
        + (shame_hits * 0.20)
        + (overwhelm_hits * 0.10)
    )

    shame_prob = clamp(
        (shame_hits * 0.45)
        + (_count_phrase_hits(lower, ["embarrassed", "ashamed"]) * 0.20)
    )

    sarcasm_prob = clamp(
        (irony_hits * 0.24)
        + (humor_hits * 0.08)
        + (_count_phrase_hits(lower, ["sure", "right", "great", "awesome"]) * 0.03)
    )

    overwhelm_prob = clamp(
        (overwhelm_hits * 0.34)
        + (_count_phrase_hits(lower, ["too much", "buried", "fried", "cooked"]) * 0.10)
        + (question * 0.03)
    )

    frustration_prob = clamp(
        (frustration_hits * 0.18)
        + (task_friction * 0.50)
        + (negative_hits * 0.04)
    )

    if humor_hits and (negative_hits > 0 or frustration_hits > 0):
        humor_mode = "dark_humor_compression"
    elif irony_hits:
        humor_mode = "wry_irony"
    elif humor_hits:
        humor_mode = "playful_release"
    else:
        humor_mode = "none"

    if vulnerability >= 0.60:
        stance = "open_or_brittle"
    elif humor_mode != "none" and frustration_prob >= 0.35:
        stance = "guarded_playful"
    elif frustration_prob >= 0.55:
        stance = "combative_or_blunt"
    else:
        stance = "direct"

    if intensity >= 0.72 or frustration_hits >= 2:
        energy = "high"
    elif len(tokens) <= 6 and humor_hits == 0 and frustration_hits == 0:
        energy = "low"
    else:
        energy = "medium"

    if frustration_prob >= 0.45 and humor_mode != "none":
        need = "banter_then_solve"
    elif task_friction >= 0.40 or solve_hits > witness_hits:
        need = "solve"
    elif vulnerability >= 0.55:
        need = "steady"
    elif question > 0:
        need = "clarify"
    else:
        need = "answer"

    if negative_hits + frustration_hits + overwhelm_hits > 0 and humor_hits > 0:
        valence = "mixed"
    elif negative_hits + frustration_hits + overwhelm_hits > 0:
        valence = "negative"
    elif humor_hits > 0:
        valence = "mixed_positive"
    else:
        valence = "neutral"

    banter_window_open = bool(
        task_friction >= 0.35
        and vulnerability < 0.45
        and playfulness >= 0.35
        and trust >= 0.40
    )

    notes = []
    if humor_mode == "dark_humor_compression":
        notes.append("Humor under pressure may be transmutation, not avoidance.")
    if sarcasm_prob >= 0.45:
        notes.append("Literal reading risk is elevated.")
    if vulnerability >= 0.55:
        notes.append("Do not over-psychologize or over-joke.")
    if task_friction >= 0.45:
        notes.append("This looks like a friction-heavy moment.")

    return {
        "valence": valence,
        "intensity": _round(intensity),
        "energy": energy,
        "stance": stance,
        "humor_mode": humor_mode,
        "sarcasm_prob": _round(sarcasm_prob),
        "frustration_prob": _round(frustration_prob),
        "overwhelm_prob": _round(overwhelm_prob),
        "shame_prob": _round(shame_prob),
        "vulnerability": _round(vulnerability),
        "task_friction": _round(task_friction),
        "need": need,
        "banter_window_open": banter_window_open,
        "notes": notes,
    }
