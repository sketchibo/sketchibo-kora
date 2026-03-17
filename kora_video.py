#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


RUNS_DIR = Path("video_runs")
PROFILES_PATH = Path("video_profiles.json")


@dataclass
class Scene:
    scene_id: str
    summary: str
    source_text: str
    word_count: int
    duration_hint_sec: int
    shot_type: str
    importance: str
    visual_prompt: str
    onscreen_text: str
    motion: str
    recommended_model: str
    variant_count: int


def load_profiles() -> Dict[str, Any]:
    if not PROFILES_PATH.exists():
        return {"providers": []}
    with PROFILES_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_text_arg(text: Optional[str], transcript_file: Optional[str]) -> str:
    if text and text.strip():
        return text.strip()
    if transcript_file:
        return Path(transcript_file).read_text(encoding="utf-8").strip()
    raise SystemExit("Provide --text or --transcript-file")


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_into_paragraphs(text: str) -> List[str]:
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if paras:
        return paras

    sents = split_sentences(text)
    if not sents:
        return []

    chunks: List[str] = []
    current: List[str] = []
    current_words = 0

    for sent in sents:
        wc = len(sent.split())
        if current and current_words + wc > 90:
            chunks.append(" ".join(current).strip())
            current = [sent]
            current_words = wc
        else:
            current.append(sent)
            current_words += wc

    if current:
        chunks.append(" ".join(current).strip())
    return chunks


def split_sentences(text: str) -> List[str]:
    raw = re.split(r"(?<=[.!?])\s+", text.strip())
    return [r.strip() for r in raw if r.strip()]


def estimate_duration(word_count: int) -> int:
    # rough spoken narration timing
    seconds = max(6, round(word_count / 2.6))
    return seconds


def classify_shot(summary: str, source_text: str, idx: int, total: int) -> str:
    lowered = f"{summary} {source_text}".lower()

    if idx == 0:
        return "hero"
    if idx == total - 1:
        return "closing"
    if any(k in lowered for k in ["why", "because", "reason", "explains", "explain", "how it works"]):
        return "concept"
    if any(k in lowered for k in ["person", "people", "human", "face", "speaker", "woman", "man"]):
        return "portrait"
    if any(k in lowered for k in ["city", "forest", "ocean", "room", "street", "landscape", "world"]):
        return "environment"
    if any(k in lowered for k in ["data", "numbers", "list", "steps", "three", "four", "five"]):
        return "text_card"
    return "documentary"


def classify_importance(idx: int, total: int, duration_hint: int) -> str:
    if idx == 0 or idx == total - 1:
        return "high"
    if duration_hint >= 16:
        return "high"
    if duration_hint >= 10:
        return "medium"
    return "low"


def summarize_chunk(chunk: str, max_words: int = 14) -> str:
    words = chunk.split()
    if len(words) <= max_words:
        return chunk
    return " ".join(words[:max_words]).strip() + "..."


def make_onscreen_text(summary: str, shot_type: str) -> str:
    if shot_type in {"hero", "closing", "text_card"}:
        cleaned = re.sub(r"\s+", " ", summary).strip()
        return cleaned[:90]
    return ""


def choose_motion(shot_type: str) -> str:
    return {
        "hero": "slow push-in",
        "portrait": "gentle push-in",
        "environment": "slow pan",
        "concept": "subtle zoom",
        "documentary": "slow drift",
        "text_card": "static hold",
        "closing": "slow pull-back",
    }.get(shot_type, "slow drift")


def choose_provider(profiles: Dict[str, Any], shot_type: str, importance: str) -> str:
    providers = profiles.get("providers", [])
    if not providers:
        return "unassigned"

    enabled = [p for p in providers if p.get("enabled", True)]
    if not enabled:
        return "unassigned"

    # high importance prefers best-quality
    if importance == "high":
        ranked = sorted(enabled, key=lambda p: p.get("quality_rank", 999))
        for p in ranked:
            if shot_type in p.get("ideal_shot_types", []):
                return p["name"]
        return ranked[0]["name"]

    # low importance prefers cheapest
    if importance == "low":
        ranked = sorted(enabled, key=lambda p: (p.get("cost_rank", 999), p.get("quality_rank", 999)))
        for p in ranked:
            if shot_type in p.get("ideal_shot_types", []):
                return p["name"]
        return ranked[0]["name"]

    # medium importance prefers balanced
    ranked = sorted(
        enabled,
        key=lambda p: (
            p.get("cost_rank", 999) + p.get("quality_rank", 999),
            p.get("speed_rank", 999),
        ),
    )
    for p in ranked:
        if shot_type in p.get("ideal_shot_types", []):
            return p["name"]
    return ranked[0]["name"]


def choose_variant_count(importance: str, shot_type: str) -> int:
    if shot_type == "text_card":
        return 0
    if importance == "high":
        return 3
    if importance == "medium":
        return 2
    return 1


def build_visual_prompt(summary: str, source_text: str, shot_type: str) -> str:
    base_style = (
        "cinematic documentary still, coherent visual storytelling, detailed composition, "
        "strong focal subject, realistic lighting, no text, high visual clarity"
    )

    shot_flavor = {
        "hero": "powerful opening frame, dramatic composition, emotionally arresting",
        "portrait": "expressive subject portrait, natural posture, subtle cinematic depth",
        "environment": "wide establishing shot, strong sense of place, atmospheric depth",
        "concept": "visual metaphor, elegant and clear, symbolic but grounded",
        "documentary": "editorial documentary frame, believable real-world detail",
        "text_card": "no generated image needed; use designed title card",
        "closing": "reflective ending frame, memorable final image, emotional resonance",
    }.get(shot_type, "documentary still")

    idea = summarize_chunk(source_text, max_words=24)
    return f"{base_style}. {shot_flavor}. Depict: {idea}"


def build_scenes(text: str, profiles: Dict[str, Any]) -> List[Scene]:
    chunks = split_into_paragraphs(text)
    scenes: List[Scene] = []

    for idx, chunk in enumerate(chunks):
        wc = len(chunk.split())
        duration_hint = estimate_duration(wc)
        summary = summarize_chunk(chunk, max_words=14)
        shot_type = classify_shot(summary, chunk, idx, len(chunks))
        importance = classify_importance(idx, len(chunks), duration_hint)
        visual_prompt = build_visual_prompt(summary, chunk, shot_type)
        onscreen_text = make_onscreen_text(summary, shot_type)
        motion = choose_motion(shot_type)
        recommended_model = choose_provider(profiles, shot_type, importance)
        variant_count = choose_variant_count(importance, shot_type)

        scenes.append(
            Scene(
                scene_id=f"scene_{idx + 1:02d}",
                summary=summary,
                source_text=chunk,
                word_count=wc,
                duration_hint_sec=duration_hint,
                shot_type=shot_type,
                importance=importance,
                visual_prompt=visual_prompt,
                onscreen_text=onscreen_text,
                motion=motion,
                recommended_model=recommended_model,
                variant_count=variant_count,
            )
        )

    return scenes


def ensure_run_dir() -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("run_%Y%m%d_%H%M%S")
    run_dir = RUNS_DIR / stamp
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def write_outputs(run_dir: Path, transcript: str, scenes: List[Scene], profiles: Dict[str, Any]) -> None:
    scene_map = [asdict(scene) for scene in scenes]

    (run_dir / "transcript.txt").write_text(transcript, encoding="utf-8")
    (run_dir / "scene_map.json").write_text(json.dumps(scene_map, indent=2, ensure_ascii=False), encoding="utf-8")

    prompt_lines: List[str] = []
    for scene in scenes:
        prompt_lines.append(f"[{scene.scene_id}]")
        prompt_lines.append(f"summary: {scene.summary}")
        prompt_lines.append(f"shot_type: {scene.shot_type}")
        prompt_lines.append(f"importance: {scene.importance}")
        prompt_lines.append(f"recommended_model: {scene.recommended_model}")
        prompt_lines.append(f"variant_count: {scene.variant_count}")
        prompt_lines.append(f"prompt: {scene.visual_prompt}")
        prompt_lines.append("")

    (run_dir / "prompt_sheet.txt").write_text("\n".join(prompt_lines).strip() + "\n", encoding="utf-8")

    edit_lines: List[str] = []
    cursor = 0
    for scene in scenes:
        start = cursor
        end = cursor + scene.duration_hint_sec
        edit_lines.append(f"[{scene.scene_id}] {start:>4}s -> {end:>4}s")
        edit_lines.append(f"summary: {scene.summary}")
        edit_lines.append(f"shot_type: {scene.shot_type}")
        edit_lines.append(f"motion: {scene.motion}")
        edit_lines.append(f"onscreen_text: {scene.onscreen_text or '(none)'}")
        edit_lines.append(f"recommended_model: {scene.recommended_model}")
        edit_lines.append("")
        cursor = end

    (run_dir / "edit_plan.txt").write_text("\n".join(edit_lines).strip() + "\n", encoding="utf-8")

    manifest = {
        "created_utc": datetime.utcnow().isoformat() + "Z",
        "run_dir": str(run_dir),
        "scene_count": len(scenes),
        "estimated_total_seconds": sum(scene.duration_hint_sec for scene in scenes),
        "profiles_loaded": [p.get("name") for p in profiles.get("providers", []) if p.get("enabled", True)],
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="KORA Video Director Phase 1 planner")
    parser.add_argument("--text", help="Transcript text inline")
    parser.add_argument("--transcript-file", help="Path to transcript text file")
    args = parser.parse_args()

    raw_text = read_text_arg(args.text, args.transcript_file)
    transcript = normalize_text(raw_text)
    profiles = load_profiles()
    scenes = build_scenes(transcript, profiles)
    run_dir = ensure_run_dir()
    write_outputs(run_dir, transcript, scenes, profiles)

    print(f"[VIDEO PLAN OK] {run_dir}")
    print(f"Scenes: {len(scenes)}")
    print(f"Estimated total duration: {sum(s.duration_hint_sec for s in scenes)} sec")


if __name__ == "__main__":
    main()
