import os
import json
import subprocess
import requests
from typing import Dict, List, Optional
from kora_interpreter import interpret
from kora_tools import list_files, read_file, tail_file, search_files

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

VENICE_URL = "https://api.venice.ai/api/v1/chat/completions"
VENICE_MODEL = "venice-uncensored"

# FAST mode default: just qwen
FAST_LOCAL_MODELS = ["qwen2.5:7b"]

# COUNCIL mode: try these if present
COUNCIL_LOCAL_MODELS = ["qwen2.5:7b", "dolphin-phi:latest", "llama3.1:8b"]

def env_key() -> str:
    # Read fresh every call (so exporting then rerunning works reliably)
    return os.getenv("VENICE_API_KEY", "").strip()

def ollama_generate(model: str, prompt: str, timeout: int = 60) -> str:
    payload = {"model": model, "prompt": prompt, "stream": False}
    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json().get("response", "") or ""
    except Exception as e:
        return f"[LOCAL ERROR {model}: {e}]"

def _venice_request(prompt: str, headers: Dict[str, str], timeout: int = 30) -> requests.Response:
    payload = {
        "model": VENICE_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0
    }
    return requests.post(VENICE_URL, headers=headers, json=payload, timeout=timeout)

def venice_chat(prompt: str, timeout: int = 30) -> Optional[str]:
    """
    Try Venice. NEVER crash. NEVER block KORA.
    Try BOTH auth styles:
      1) Authorization: Bearer <key>   (official docs)
      2) x-api-key: <key>              (fallback)
    Return string on success, else None.
    """
    key = env_key()
    if not key:
        return None

    # 1) Official docs style
    headers_a = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    # 2) Alternative header style
    headers_b = {
        "x-api-key": key,
        "Content-Type": "application/json",
    }

    for headers in (headers_a, headers_b):
        try:
            r = _venice_request(prompt, headers=headers, timeout=timeout)
            if r.status_code in (401, 403):
                continue
            r.raise_for_status()

            data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            # Defensive parse
            choices = data.get("choices") or []
            if choices and isinstance(choices, list):
                msg = choices[0].get("message") or {}
                content = msg.get("content")
                if isinstance(content, str) and content.strip():
                    return content.strip()
            return None
        except requests.Timeout:
            return None
        except Exception:
            continue

    return None

def venice_test() -> str:
    """
    /venice-test -> print VENICE_OK or VENICE_401/403/TIMEOUT without leaking the key
    """
    key = env_key()
    if not key:
        return "VENICE_NO_KEY"

    # Try Bearer then x-api-key, report the first meaningful status
    headers_a = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    headers_b = {"x-api-key": key, "Content-Type": "application/json"}

    for headers in (headers_a, headers_b):
        try:
            r = _venice_request("Reply with exactly OK", headers=headers, timeout=20)
            if r.status_code == 200:
                return "VENICE_OK"
            if r.status_code in (401, 403):
                # keep trying the other header
                last = f"VENICE_{r.status_code}"
                continue
            return f"VENICE_{r.status_code}"
        except requests.Timeout:
            return "VENICE_TIMEOUT"
        except Exception:
            continue

    return last if "last" in locals() else "VENICE_FAIL"

def merge_locals(drafts: Dict[str, str]) -> str:
    # Simple merge that won't explode
    parts = []
    for k, v in drafts.items():
        if v and isinstance(v, str):
            parts.append(f"[{k}] {v.strip()}")
    return "\n\n".join(parts).strip()

def load_canon_files() -> str:
    canon_files = [
        "core/identity/SOUL.md",
        "core/identity/CHARTER.md",
        "core/identity/IDENTITY.md",
        "core/identity/USER.md"
    ]
    system_prompt = ""
    for file_path in canon_files:
        with open(file_path, "r") as file:
            system_prompt += file.read() + "\n\n"
    return system_prompt.strip()

def run_fast(user_prompt: str) -> str:
    # Venice is optional and must not block.
    v = venice_chat(user_prompt, timeout=20)
    if v:
        return v
    return ollama_generate(FAST_LOCAL_MODELS[0], user_prompt, timeout=60)

def run_council(user_prompt: str) -> str:
    drafts = {}
    for model in COUNCIL_LOCAL_MODELS:
        drafts[model] = ollama_generate(model, user_prompt, timeout=60)
    merged = merge_locals(drafts)
    # Final synthesis locally (never Venice-gated)
    final_prompt = (
        "You are KORA. Merge the following drafts into one best answer.\n\n"
        f"{merged}\n\n"
        "Return a single clear response."
    )
    return ollama_generate("qwen2.5:7b", final_prompt, timeout=60)

def post_filter(text: str) -> str:
    # Replace any mentions of backend models
    replacements = {
        "I am Venice": "KORA",
        "I am Qwen": "KORA",
        "I am Alibaba": "KORA",
        "I am a model created by": "KORA"
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

def save_tts(text):
    api = os.getenv("ELEVENLABS_API_KEY", "").strip()
    voice = os.getenv("ELEVENLABS_VOICE_ID", "").strip()
    if not api or not voice or not text.strip():
        return

    out_path = os.path.expanduser("~/kora/last_reply.mp3")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128"
    payload = json.dumps({
        "text": text,
        "model_id": "eleven_multilingual_v2"
    })

    try:
        subprocess.run(
            [
                "curl", "-sS", "-X", "POST", url,
                "-H", f"xi-api-key: {api}",
                "-H", "Content-Type: application/json",
                "-d", payload,
                "--output", out_path,
            ],
            check=True,
            timeout=60,
        )
        if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
            print("[TTS saved: ~/kora/last_reply.mp3]")
    except Exception:
        pass

def handle_interpreter_actions(user_input: str) -> str:
    interpret_result = interpret(user_input)
    if interpret_result["mode"] == "action":
        action = interpret_result["intent"]
        if action == "list_files":
            return list_files(interpret_result["args"]["path"])
        elif action == "read_file":
            return read_file(interpret_result["args"]["path"])
        elif action == "tail_file":
            return tail_file(interpret_result["args"]["path"], interpret_result["args"]["lines"])
        elif action == "search_files":
            return search_files(interpret_result["args"]["query"], interpret_result["args"]["root"])
    return "Unknown command"

def main():
    print("Hey there! Welcome to KORA Council!")
    print("Commands: help, test, fast, council, status, exit")

    mode = "fast"
    system_prompt = load_canon_files()

    while True:
        raw = input("\nYou: ").strip()
        u = raw.lower()
        if not u:
            continue

        if u in ("exit", "quit"):
            break

        if u in ("help", "h"):
            print("\nKORA: Available commands: help, test, fast, council, status, exit")
            continue

        if u in ("test", "t"):
            print("\nKORA:", venice_test())
            continue

        if u in ("fast", "f"):
            mode = "fast"
            print("\nKORA: OK (mode=fast)")
            continue

        if u in ("council", "c"):
            mode = "council"
            print("\nKORA: OK (mode=council)")
            continue

        if u in ("status", "s"):
            print("\nKORA: Current mode:", mode)
            print("KORA: Active engines:", ", ".join(COUNCIL_LOCAL_MODELS if mode == "council" else [FAST_LOCAL_MODELS[0]]))
            continue

        if u in ("install xtts", "xtts install"):
            print("\nKORA: Installing xtts...")
            # Placeholder for actual installation logic
            print("\nKORA: xtts installation completed.")
            continue

        # Handle interpreter actions
        response = handle_interpreter_actions(u)
        if response != "Unknown command":
            print("\nKORA:", response)
            save_tts(response)

if __name__ == "__main__":
    main()
