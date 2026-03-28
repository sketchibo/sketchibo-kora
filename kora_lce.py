"""
KORA Life Compression Engine (LCE) - v0.1 Scaffold
====================================================
Concepts from session: Mar 26, 2026

Core ideas captured:
- Probationary learning phase (2-4 weeks of structured intake)
- Life Compression Engine: simulate user's lived days in compressed time
- Conscience of Reason: cross-reference intention vs outcome to surface truth
- Dialectical truth: two things can be true at once
- Internal vs external dialogue layer
- Credibility assessment without judgment
- User sovereignty: all data stays local (ledger-based, append-only)

This is a scaffold. It defines the architecture and data shapes.
Fill in the logic as KORA grows.
"""

import json
import uuid
from datetime import datetime, date
from pathlib import Path
from typing import Optional

# ── Paths (local-first, no cloud required) ──────────────────────────────────
LEDGER_PATH = Path("memory/lce_ledger.jsonl")
PROFILE_PATH = Path("memory/lce_profile.json")
LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)


# ── Core data shapes ────────────────────────────────────────────────────────

def empty_profile(user_name: str = "user") -> dict:
    """
    The user model KORA builds during the probationary phase.
    This is the 'lived experience' substrate.
    """
    return {
        "user_name": user_name,
        "days_lived": None,           # calculated from DOB when provided
        "dob": None,                  # date of birth (optional, user-provided)
        "probationary_phase": {
            "active": True,
            "start_date": datetime.now().isoformat(),
            "target_duration_days": 14,
            "sessions_completed": 0,
            "intake_complete": False,
        },
        "internal_dialogue": [],      # what user says they were THINKING
        "external_dialogue": [],      # what user actually said/did
        "lived_events": [],           # key moments with weight scores
        "credibility_signals": [],    # patterns of honesty/rationalization
        "conscience_calibration": {
            "guilt_sensitivity": None,     # high / medium / low / absent
            "empathy_range": None,         # broad / selective / narrow
            "rationalization_patterns": [],
        },
        "dialectical_truths": [],     # moments where 2 things were both true
        "compression_runs": [],       # log of simulation runs
    }


def append_ledger(entry: dict):
    """Append-only memory. Nothing is deleted. Everything is auditable."""
    entry["timestamp"] = datetime.now().isoformat()
    entry["id"] = str(uuid.uuid4())[:8]
    with open(LEDGER_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


def load_profile() -> dict:
    if PROFILE_PATH.exists():
        return json.loads(PROFILE_PATH.read_text())
    return empty_profile()


def save_profile(profile: dict):
    PROFILE_PATH.write_text(json.dumps(profile, indent=2))


# ── Probationary Phase ──────────────────────────────────────────────────────

INTAKE_QUESTIONS = [
    # Round 1: grounding
    "How many years have you been alive? And roughly, what decade were you born in?",
    "What's the earliest memory you have that actually meant something to you?",
    "Growing up, what was the environment like — stable, chaotic, somewhere in between?",
    "Who was the first person in your life you really trusted?",

    # Round 2: pattern recognition
    "What's a decision you made that you told yourself was for good reasons — but looking back, you're not sure?",
    "When something goes wrong in your life, what's your first instinct — look inward or look outward?",
    "Have you ever done something that hurt someone else, and if so, how did you process that?",
    "What do you want most in your life right now — be honest, not what sounds good.",

    # Round 3: internal/external dialogue gap
    "Think of a conflict you had with someone important. What did you say out loud? And what were you actually thinking?",
    "Is there something you believe about yourself that almost nobody else knows?",
    "What's the gap between who you are and who you present yourself as?",

    # Round 4: conscience calibration
    "Have you ever done something you knew was wrong and felt no guilt about it? What was it?",
    "Have you ever felt guilty about something that most people would say was fine?",
    "When you imagine the best version of your life — what does a normal Tuesday look like?",
]


def get_next_intake_question(profile: dict) -> Optional[str]:
    """Return the next unanswered intake question, or None if complete."""
    answered = len(profile.get("internal_dialogue", []))
    if answered < len(INTAKE_QUESTIONS):
        return INTAKE_QUESTIONS[answered]
    return None


def record_intake_response(profile: dict, question: str, response: str):
    """
    Store the user's answer to an intake question.
    Tag it as internal_dialogue (self-reported thought/memory).
    """
    entry = {
        "type": "intake",
        "question": question,
        "response": response,
        "weight": 1.0,   # can be adjusted by conscience layer later
    }
    profile["internal_dialogue"].append(entry)
    append_ledger({"event": "intake_response", **entry})
    save_profile(profile)


# ── Life Compression Engine ─────────────────────────────────────────────────

def calculate_days_lived(dob_str: str) -> int:
    """How many days has this person been alive."""
    dob = date.fromisoformat(dob_str)
    return (date.today() - dob).days


def compress_life(profile: dict) -> dict:
    """
    Core LCE function.

    Takes everything KORA knows about the user and runs a compressed
    simulation of their lived experience. Output is a 'life model'
    that KORA reasons FROM, not just about.

    This is the function that gives KORA its 'gut'.

    v0.1: returns a structured summary.
    Future: runs as an agent loop with scenario simulation.
    """
    days = profile.get("days_lived") or 0
    events = profile.get("lived_events", [])
    internal = profile.get("internal_dialogue", [])

    # Weight events by emotional significance
    weighted_events = sorted(events, key=lambda e: e.get("weight", 1.0), reverse=True)
    high_weight = [e for e in weighted_events if e.get("weight", 1.0) >= 2.0]

    compression = {
        "days_simulated": days,
        "years_simulated": round(days / 365.25, 1) if days else 0,
        "high_impact_events": high_weight[:10],   # top 10 formative moments
        "internal_voice_samples": internal[:5],   # first 5 self-reported thoughts
        "conscience_profile": profile.get("conscience_calibration", {}),
        "dialectical_truths_found": len(profile.get("dialectical_truths", [])),
        "compression_quality": _assess_compression_quality(profile),
        "run_timestamp": datetime.now().isoformat(),
    }

    profile["compression_runs"].append(compression)
    append_ledger({"event": "compression_run", "summary": compression})
    save_profile(profile)
    return compression


def _assess_compression_quality(profile: dict) -> str:
    """
    How complete is the life model?
    Returns: 'insufficient' / 'partial' / 'workable' / 'strong'
    """
    score = 0
    if profile.get("dob"):                               score += 1
    if len(profile.get("internal_dialogue", [])) >= 8:  score += 2
    if len(profile.get("lived_events", [])) >= 5:       score += 2
    if profile["conscience_calibration"].get("guilt_sensitivity"): score += 1
    if len(profile.get("dialectical_truths", [])) >= 1: score += 1

    if score <= 1: return "insufficient"
    if score <= 3: return "partial"
    if score <= 5: return "workable"
    return "strong"


# ── Conscience of Reason ────────────────────────────────────────────────────

def evaluate_intention_vs_outcome(
    profile: dict,
    stated_intention: str,
    actual_outcome: str,
    user_assessment: str,   # how the user describes it now
) -> dict:
    """
    Cross-reference what the user said they intended vs what happened.
    Surface the gap without judgment. Let the user sit with it.

    This is the core conscience mechanism.
    Not a lie detector. A clarity engine.
    """
    evaluation = {
        "stated_intention": stated_intention,
        "actual_outcome": actual_outcome,
        "user_assessment": user_assessment,
        "gap_detected": False,
        "gap_description": None,
        "dialectical": False,
        "followup_question": None,
    }

    # Basic gap detection (v0.1: keyword heuristic, future: LLM reasoning)
    positive_words = ["good", "help", "better", "right", "love", "protect"]
    negative_outcomes = ["hurt", "bad", "wrong", "failed", "lost", "broke"]

    intention_positive = any(w in stated_intention.lower() for w in positive_words)
    outcome_negative = any(w in actual_outcome.lower() for w in negative_outcomes)

    if intention_positive and outcome_negative:
        evaluation["gap_detected"] = True
        evaluation["gap_description"] = (
            "You said your intention was good, but the outcome caused harm. "
            "That gap is worth sitting with — not to assign blame, but to understand."
        )
        evaluation["followup_question"] = (
            "When you look back at the moment you made that choice, "
            "what were you actually thinking — not what you wished you were thinking?"
        )

    # Check for dialectical truth
    if "but" in user_assessment.lower() or "both" in user_assessment.lower():
        evaluation["dialectical"] = True
        profile["dialectical_truths"].append({
            "intention": stated_intention,
            "outcome": actual_outcome,
            "user_words": user_assessment,
        })

    append_ledger({"event": "conscience_evaluation", **evaluation})
    save_profile(profile)
    return evaluation


# ── Internal vs External Dialogue ──────────────────────────────────────────

def record_external_event(profile: dict, description: str, what_was_said: str):
    """What actually happened and what the user said out loud."""
    entry = {
        "type": "external",
        "description": description,
        "said": what_was_said,
        "weight": 1.0,
    }
    profile["external_dialogue"].append(entry)
    profile["lived_events"].append(entry)
    append_ledger({"event": "external_recorded", **entry})
    save_profile(profile)


def record_internal_thought(profile: dict, context: str, actual_thought: str):
    """What the user was actually thinking — the internal layer."""
    entry = {
        "type": "internal",
        "context": context,
        "thought": actual_thought,
        "weight": 1.5,   # internal thought weighted higher — harder to access
    }
    profile["internal_dialogue"].append(entry)
    append_ledger({"event": "internal_recorded", **entry})
    save_profile(profile)


# ── Simple CLI for testing ──────────────────────────────────────────────────

if __name__ == "__main__":
    print("KORA Life Compression Engine — v0.1")
    print("=====================================\n")

    profile = load_profile()

    if profile["probationary_phase"]["active"]:
        question = get_next_intake_question(profile)
        if question:
            print(f"KORA: {question}")
            response = input("You: ").strip()
            if response:
                record_intake_response(profile, question, response)
                print("\n[Response logged to ledger.]\n")
        else:
            print("Probationary intake complete. Running first compression...\n")
            profile["probationary_phase"]["intake_complete"] = True
            profile["probationary_phase"]["active"] = False
            save_profile(profile)
            result = compress_life(profile)
            print(f"Compression quality: {result['compression_quality']}")
            print(f"Days simulated: {result['days_simulated']}")
    else:
        result = compress_life(profile)
        print(f"Life model status: {result['compression_quality']}")
        print(f"High-impact events logged: {len(result['high_impact_events'])}")
        print(f"Dialectical truths found: {result['dialectical_truths_found']}")
