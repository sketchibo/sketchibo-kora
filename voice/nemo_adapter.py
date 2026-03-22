from typing import Dict, Any, Optional

def nemo_available() -> bool:
    try:
        import nemo.collections.asr  # noqa: F401
        return True
    except Exception:
        return False

def transcribe_audio(audio_path: str) -> Dict[str, Any]:
    if not nemo_available():
        return {
            "ok": False,
            "engine": "nemo",
            "error": "NeMo is not installed in this environment yet."
        }

    return {
        "ok": False,
        "engine": "nemo",
        "error": "NeMo adapter scaffold is present, but decoding is not wired in yet."
    }

def extract_vocal_cues(transcript: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    meta = meta or {}
    lower = (transcript or "").lower()

    return {
        "ok": True,
        "engine": "nemo",
        "pause_heavy": bool(meta.get("pause_heavy", False)),
        "hesitation_markers": sum(lower.count(x) for x in ["um", "uh", "..."]),
        "laughter_markers": sum(lower.count(x) for x in ["haha", "lol", "lmao"]),
        "cue_confidence": float(meta.get("cue_confidence", 0.0)),
        "notes": "Treat audio cues as helpful but untrusted."
    }
