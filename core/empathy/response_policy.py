from typing import Dict, Any

def _round(v: float) -> float:
    return round(float(v), 3)

def decide_response_policy(
    user_text: str,
    state: Dict[str, Any],
    rapport: Dict[str, Any] | None = None,
    classification: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    rapport = rapport or {}
    classification = classification or {}

    trust = float(rapport.get("trust_level", 0.5))
    playfulness = float(rapport.get("playfulness_budget", 0.4))
    challenge_budget = float(rapport.get("challenge_budget", 0.4))
    interpretation_budget = float(rapport.get("interpretation_budget", 0.35))
    process_companion_tolerance = float(rapport.get("process_companion_tolerance", 0.5))

    vulnerability = float(state.get("vulnerability", 0.0))
    friction = float(state.get("task_friction", 0.0))
    shame_prob = float(state.get("shame_prob", 0.0))
    humor_mode = state.get("humor_mode", "none")
    banter_window_open = bool(state.get("banter_window_open", False))

    input_mode = classification.get("mode", "general_chat")

    response_mode = "just_answer"
    banter_allowed = False
    banter_style = "none"
    do_not_psychologize = False

    if input_mode == "shell_blob":
        response_mode = "just_answer"
        do_not_psychologize = True
    elif input_mode == "voice_identity":
        response_mode = "warm_direct"
        do_not_psychologize = True
    elif input_mode == "task_debug":
        response_mode = "steady_practical"
    elif input_mode == "meta_system_talk":
        response_mode = "warm_direct"
        do_not_psychologize = True
    elif input_mode == "rapport_banter":
        response_mode = "wry_companion"
        banter_allowed = True
        banter_style = "light_banter"

    if vulnerability >= 0.65 or shame_prob >= 0.60:
        response_mode = "warm_direct"
        banter_allowed = False
        do_not_psychologize = True
    elif input_mode not in {"shell_blob", "voice_identity", "task_debug"}:
        if friction >= 0.55 and banter_window_open:
            response_mode = "wry_companion"
            banter_allowed = True
            banter_style = "challenge_banter"
        elif friction >= 0.40:
            response_mode = "steady_practical"

    if humor_mode == "dark_humor_compression" and friction >= 0.35 and playfulness >= 0.45:
        if input_mode not in {"shell_blob", "voice_identity"}:
            banter_allowed = True
            if banter_style == "none":
                banter_style = "challenge_banter"

    if vulnerability >= 0.50:
        banter_allowed = False
        banter_style = "none"

    if interpretation_budget < 0.40:
        do_not_psychologize = True

    challenge_level = min(challenge_budget, 0.55 if vulnerability < 0.45 else 0.20)
    companionship_level = min(process_companion_tolerance, 0.80 if friction >= 0.35 else 0.40)

    return {
        "input_mode": input_mode,
        "response_mode": response_mode,
        "banter_allowed": banter_allowed,
        "banter_style": banter_style,
        "challenge_level": _round(challenge_level),
        "companionship_level": _round(companionship_level),
        "do_not_psychologize": do_not_psychologize,
        "trust_level": _round(trust),
        "playfulness_budget": _round(playfulness),
        "anthropomorphic_translation_ok": True,
    }

def render_empathy_block(
    state: Dict[str, Any],
    policy: Dict[str, Any],
    classification: Dict[str, Any] | None = None,
) -> str:
    classification = classification or {}

    lines = [
        "[INTERACTION READ]",
        "This is a fallible estimate, not certainty.",
        f"Input mode: {policy.get('input_mode', classification.get('mode', 'general_chat'))}",
        f"Input mode confidence: {classification.get('confidence', 0.0)}",
        f"Tone guess: {state.get('stance', 'direct')}",
        f"Valence: {state.get('valence', 'neutral')}",
        f"Energy: {state.get('energy', 'medium')}",
        f"Humor mode: {state.get('humor_mode', 'none')}",
        f"Task friction: {state.get('task_friction', 0.0)}",
        f"Vulnerability: {state.get('vulnerability', 0.0)}",
        f"Likely need right now: {state.get('need', 'answer')}",
        f"Response mode to use: {policy.get('response_mode', 'just_answer')}",
        f"Banter allowed: {policy.get('banter_allowed', False)}",
        f"Banter style: {policy.get('banter_style', 'none')}",
        f"Challenge level: {policy.get('challenge_level', 0.0)}",
        f"Companionship level: {policy.get('companionship_level', 0.0)}",
    ]

    if policy.get("do_not_psychologize"):
        lines.append("Do not over-psychologize. Prefer grounded practical language.")

    if policy.get("banter_allowed"):
        lines.append("At most one brief wry line is allowed if it helps.")
    else:
        lines.append("Keep the tone literal and clean. No unnecessary joke layer.")

    mode_notes = classification.get("notes") or []
    if mode_notes:
        lines.append("Mode notes: " + " | ".join(mode_notes))

    notes = state.get("notes") or []
    if notes:
        lines.append("State notes: " + " | ".join(notes))

    lines.append("Never claim to know exactly how the user feels.")
    lines.append("Interpret boldly enough to help, but humbly enough to be corrected.")
    lines.append("[/INTERACTION READ]")
    return "\n".join(lines)
