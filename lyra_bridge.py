"""
lyra_bridge.py — bidirectional relay between Lyra (phone/ntfy) and Kora.

Phone → ntfy topic NTFY_LYRA_IN → this script → Kora → ntfy topic NTFY_KORA_OUT → phone

Add to .env:
    NTFY_LYRA_IN=kora-lyra-in-kayle
    NTFY_KORA_OUT=kora-lyra-out-kayle
    NTFY_HOST=https://ntfy.sh   (optional, default: https://ntfy.sh)

Run:
    python3 lyra_bridge.py
"""

import json
import os
import sys
import time
from datetime import datetime

import requests
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"))

NTFY_HOST    = os.getenv("NTFY_HOST", "https://ntfy.sh").rstrip("/")
TOPIC_IN     = os.getenv("NTFY_LYRA_IN",  "kora-lyra-in-kayle")
TOPIC_OUT    = os.getenv("NTFY_KORA_OUT", "kora-lyra-out-kayle")
FACTS_PATH   = os.path.join(BASE_DIR, "memory", "facts.jsonl")


# ── memory ────────────────────────────────────────────────────────────────────

def save_fact(text: str, source: str) -> None:
    os.makedirs(os.path.dirname(FACTS_PATH), exist_ok=True)
    row = {
        "ts":     datetime.now().isoformat(),
        "kind":   "fact",
        "source": source,
        "text":   text,
    }
    with open(FACTS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


# ── ntfy publish ──────────────────────────────────────────────────────────────

def publish(text: str, title: str = "Kora") -> None:
    url = f"{NTFY_HOST}/{TOPIC_OUT}"
    try:
        requests.post(
            url,
            data=text.encode("utf-8"),
            headers={
                "Title":    title,
                "Priority": "default",
            },
            timeout=10,
        )
        print(f"[→ phone] {text[:80]}", flush=True)
    except Exception as e:
        print(f"[publish error] {e}", flush=True)


# ── kora response ─────────────────────────────────────────────────────────────

def kora_reply(lyra_text: str) -> str:
    try:
        from kora import run_fast, post_filter
        prompt = f"[Lyra said]: {lyra_text}"
        return post_filter(run_fast(prompt))
    except Exception as e:
        return f"[kora error: {e}]"


# ── ntfy subscribe (SSE stream) ───────────────────────────────────────────────

def listen() -> None:
    url = f"{NTFY_HOST}/{TOPIC_IN}/sse"
    print(f"[lyra_bridge] listening on {url}", flush=True)
    print(f"[lyra_bridge] replies → {NTFY_HOST}/{TOPIC_OUT}", flush=True)

    while True:
        try:
            with requests.get(url, stream=True, timeout=90) as resp:
                resp.raise_for_status()
                for raw_line in resp.iter_lines():
                    if not raw_line:
                        continue
                    line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
                    if not line.startswith("data:"):
                        continue
                    payload = line[len("data:"):].strip()
                    if not payload or payload == "{}":
                        continue
                    try:
                        msg = json.loads(payload)
                    except Exception:
                        continue

                    event = msg.get("event", "message")
                    if event != "message":
                        continue

                    text = msg.get("message", "").strip()
                    if not text:
                        continue

                    print(f"[← Lyra] {text[:120]}", flush=True)
                    save_fact(text, source="lyra")

                    reply = kora_reply(text)
                    save_fact(reply, source="kora_to_lyra")
                    publish(reply)

        except requests.exceptions.Timeout:
            # normal — ntfy keeps connections alive ~60s, just reconnect
            pass
        except Exception as e:
            print(f"[stream error] {e} — reconnecting in 5s", flush=True)
            time.sleep(5)


if __name__ == "__main__":
    listen()
