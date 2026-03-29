import kora_tools
import os
import sys
import json
import glob
import platform
import subprocess
from datetime import datetime
from typing import Dict, Optional, Any
from kora_interpreter import interpret
import kora_tools
from core.empathy.state_estimator import estimate_state
from core.empathy.response_policy import decide_response_policy, render_empathy_block
from core.empathy.input_classifier import classify_input

import requests
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"))

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
VENICE_URL = "https://api.venice.ai/api/v1/chat/completions"
VENICE_MODEL = "venice-uncensored"
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)

FAST_LOCAL_MODELS = ["qwen2.5:7b"]
COUNCIL_LOCAL_MODELS = ["qwen2.5:7b", "dolphin-phi:latest", "llama3.1:8b"]


def env_key() -> str:
    return os.getenv("VENICE_API_KEY", "").strip()


def gemini_key() -> str:
    return (
        os.getenv("GOOGLE_API_KEY", "").strip()
        or os.getenv("GEMINI_API_KEY", "").strip()
    )



STARTUP_CONTEXT_FILE = "memory/startup_context.json"

def load_startup_context(path=STARTUP_CONTEXT_FILE):
    try:
        import json
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        return {"_startup_context_error": str(e)}

def startup_context_text(ctx):
    if not ctx:
        return ""

    user = (ctx.get("user") or {}).get("name", "unknown")
    project = (ctx.get("project") or {}).get("name", "unknown")
    principles = ctx.get("pinned_principles") or []
    goals = ctx.get("active_goals") or []
    tasks = ctx.get("open_tasks") or []

    lines = [
        "[STARTUP CONTEXT]",
        f"User: {user}",
        f"Project: {project}",
    ]

    if principles:
        lines.append("Principles: " + "; ".join(principles[:4]))
    if goals:
        lines.append("Active goal: " + goals[0])
    if tasks:
        lines.append("Open task: " + tasks[0])
    if "_startup_context_error" in ctx:
        lines.append("Startup context error: " + str(ctx["_startup_context_error"]))

    lines.append("[/STARTUP CONTEXT]")
    return "\n".join(lines)


def startup_context_brief(ctx):
    if not ctx:
        return ""

    user = (ctx.get("user") or {}).get("name", "unknown")
    project = (ctx.get("project") or {}).get("name", "unknown")
    principles = ctx.get("pinned_principles") or []

    lines = [
        "[STARTUP BRIEF]",
        f"User: {user}",
        f"Project: {project}",
    ]

    if principles:
        lines.append("Principles: " + "; ".join(principles[:3]))

    lines.append("[/STARTUP BRIEF]")
    return "\n".join(lines)

def print_startup_context(ctx):
    block = startup_context_text(ctx)
    if block:
        print("\n" + block + "\n")
    else:
        print("\n[startup] no startup context loaded\n")


STARTUP_CONTEXT = load_startup_context()


PERSON_MODEL_PATH = os.path.join(BASE_DIR, "memory", "person_model.json")
RAPPORT_STATE_PATH = os.path.join(BASE_DIR, "memory", "rapport_state.json")
TRAJECTORY_PATH = os.path.join(BASE_DIR, "memory", "trajectory.json")
SIGNALS_PATH = os.path.join(BASE_DIR, "memory", "signals.jsonl")

def load_json_file(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except Exception:
        return default

def load_person_model() -> Dict[str, Any]:
    return load_json_file(PERSON_MODEL_PATH, {})

def load_rapport_state() -> Dict[str, Any]:
    return load_json_file(RAPPORT_STATE_PATH, {})

def load_trajectory_state() -> Dict[str, Any]:
    return load_json_file(TRAJECTORY_PATH, {})

def log_signal(user_text: str, state: Dict[str, Any], policy: Dict[str, Any], mode: str, trajectory_hint: str = "", classification: Dict[str, Any] | None = None) -> None:
    os.makedirs(os.path.dirname(SIGNALS_PATH), exist_ok=True)
    row = {
        "ts": datetime.now().isoformat(),
        "mode": mode,
        "raw_input": user_text,
        "trajectory_hint": trajectory_hint,
        "state": state,
        "policy": policy,
        "classification": classification or {},
    }
    try:
        with open(SIGNALS_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        pass

def empathy_context_block(user_text: str, mode: str = "chat") -> str:
    person_model = load_person_model()
    rapport_state = load_rapport_state()
    trajectory_state = load_trajectory_state()
    classification = classify_input(user_text)

    state = estimate_state(user_text, person_model=person_model, rapport=rapport_state)
    policy = decide_response_policy(user_text, state, rapport=rapport_state, classification=classification)
    block = render_empathy_block(state, policy, classification=classification)

    trajectory_hint = str((trajectory_state or {}).get("current_arc", "")).strip()
    if trajectory_hint:
        block = block + "\nTrajectory hint: " + trajectory_hint

    log_signal(user_text, state, policy, mode=mode, trajectory_hint=trajectory_hint, classification=classification)
    return block

def ollama_generate(model: str, prompt: str, timeout: int = 180) -> str:
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
        "temperature": 0,
    }
    return requests.post(VENICE_URL, headers=headers, json=payload, timeout=timeout)


def venice_chat(prompt: str, timeout: int = 30) -> Optional[str]:
    key = env_key()
    if not key:
        return None

    headers_a = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
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
    key = env_key()
    if not key:
        return "VENICE_NO_KEY"

    headers_a = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    headers_b = {"x-api-key": key, "Content-Type": "application/json"}

    last = "VENICE_FAIL"
    for headers in (headers_a, headers_b):
        try:
            r = _venice_request("Reply with exactly OK", headers=headers, timeout=20)
            if r.status_code == 200:
                return "VENICE_OK"
            if r.status_code in (401, 403):
                last = f"VENICE_{r.status_code}"
                continue
            return f"VENICE_{r.status_code}"
        except requests.Timeout:
            return "VENICE_TIMEOUT"
        except Exception:
            continue

    return last


def gemini_generate(prompt: str, timeout: int = 30) -> str:
    key = gemini_key()
    if not key:
        return "GEMINI_NO_KEY"

    url = f"{GEMINI_URL}?key={key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    try:
        r = requests.post(url, json=payload, timeout=timeout)
        if r.status_code == 401:
            return "GEMINI_401"
        if r.status_code == 403:
            return "GEMINI_403"
        r.raise_for_status()

        data = r.json()
        candidates = data.get("candidates") or []
        if not candidates:
            return "GEMINI_EMPTY"

        content = (candidates[0] or {}).get("content") or {}
        parts = content.get("parts") or []
        text = "".join(
            p.get("text", "") for p in parts if isinstance(p, dict)
        ).strip()

        return text or "GEMINI_EMPTY"
    except requests.Timeout:
        return "GEMINI_TIMEOUT"
    except Exception as e:
        return f"GEMINI_FAIL: {e}"


def gemini_test() -> str:
    out = gemini_generate("Reply with exactly GEMINI_OK", timeout=20)
    if "GEMINI_OK" in out:
        return "GEMINI_OK"
    return out


def merge_locals(drafts: Dict[str, str]) -> str:
    parts = []
    for k, v in drafts.items():
        if v and isinstance(v, str):
            parts.append(f"[{k}] {v.strip()}")
    return "\n\n".join(parts).strip()



def latest_journal_path() -> Optional[str]:
    files = sorted(glob.glob(os.path.join(BASE_DIR, "memory", "journal", "*.md")))
    return files[-1] if files else None


def facts_preview(limit: int = 8) -> str:
    path = os.path.join(BASE_DIR, "memory", "facts.jsonl")
    if not os.path.exists(path):
        return ""

    items = []
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
                text = obj.get("text") or raw
            except Exception:
                text = raw
            items.append(f"- {text}")

    return "\n".join(items[-limit:])


def load_canon_files() -> str:
    chunks = []

    canon_files = [
        "core/identity/SOUL.md",
        "core/identity/CHARTER.md",
        "core/identity/IDENTITY.md",
        "core/identity/USER.md",
        "core/profiles/memoic_profile.md",
        "core/profiles/persona_profile.md",
    ]

    for file_path in canon_files:
        full = os.path.join(BASE_DIR, file_path)
        if os.path.exists(full):
            with open(full, "r", encoding="utf-8") as file:
                text = file.read().strip()
                if text:
                    chunks.append(f"## {file_path}\n{text}")

    voice_profile_path = os.path.join(BASE_DIR, "core", "profiles", "voice_profile.json")
    if os.path.exists(voice_profile_path):
        with open(voice_profile_path, "r", encoding="utf-8") as file:
            text = file.read().strip()
            if text:
                chunks.append("## core/profiles/voice_profile.json\n" + text)

    guidance_path = os.path.join(BASE_DIR, "memory", "guidance.md")
    if os.path.exists(guidance_path):
        with open(guidance_path, "r", encoding="utf-8") as file:
            text = file.read().strip()
            if text:
                chunks.append("## memory/guidance.md\n" + text)

    journal_path = latest_journal_path()
    if journal_path and os.path.exists(journal_path):
        with open(journal_path, "r", encoding="utf-8") as file:
            text = file.read().strip()
            if text:
                rel = os.path.relpath(journal_path, BASE_DIR)
                chunks.append(f"## {rel}\n{text}")

    facts = facts_preview()
    if facts:
        chunks.append("## memory/facts.jsonl\n" + facts)

    return "\n\n".join(chunks).strip()

def load_voice_profile() -> Dict[str, Any]:
    path = os.path.join(BASE_DIR, "core", "profiles", "voice_profile.json")
    if not os.path.exists(path):
        return {
            "enabled": False,
            "backend": "none",
            "voice_name": "kora",
            "mode": "optional",
        }
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {
        "enabled": False,
        "backend": "none",
        "voice_name": "kora",
        "mode": "optional",
    }


def speak(text: str) -> str:
    profile = load_voice_profile()
    if not profile.get("enabled"):
        return ""
    backend = str(profile.get("backend", "none")).strip().lower()
    if backend in ("", "none", "off", "disabled"):
        return ""
    # Placeholder hook: real TTS backend can be attached later.
    return ""


def post_filter(text: str) -> str:
    replacements = {
        "I am Venice": "KORA",
        "I am Qwen": "KORA",
        "I am Alibaba": "KORA",
        "I am a model created by": "KORA",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def looks_like_shell_or_log(text: str) -> bool:
    markers = [
        "$ ",
        "sudo ",
        "apt ",
        "pip ",
        "pip3 ",
        "python3 ",
        "cd ",
        "ssh ",
        "scp ",
        "nano ",
        "cat ",
        "grep ",
        "ls ",
        "cp ",
        "mv ",
        "source ",
        "deactivate",
        "kayle@vultr",
        "(sgpt)",
        "Traceback",
        "ModuleNotFoundError",
        "Connection reset by peer",
        "Broken pipe",
    ]
    stripped = text.strip()
    shell_prefixes = (
        "sudo ", "apt ", "pip ", "pip3 ", "python3 ", "cd ",
        "ssh ", "scp ", "nano ", "cat ", "grep ", "ls ",
        "cp ", "mv ", "source ", "deactivate"
    )
    if stripped.startswith(shell_prefixes):
        return True
    if any(x in text for x in ("Traceback", "ModuleNotFoundError", "Connection reset by peer", "Broken pipe")):
        return True
    hits = sum(1 for m in markers if m in text)
    return hits >= 2 or ("\n" in text and hits >= 1)


def looks_like_big_paste(text: str) -> bool:
    return len(text) > 700 and "\n" in text


def safe_cmd(cmd: str) -> str:
    try:
        return subprocess.check_output(
            cmd,
            shell=True,
            text=True,
            stderr=subprocess.STDOUT,
            cwd=BASE_DIR,
        ).strip()
    except Exception as e:
        return f"[CMD ERROR] {e}"


def generate_snapshot() -> str:
    os.makedirs(os.path.join(BASE_DIR, "snapshots"), exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join("snapshots", f"snapshot_{ts}.json")

    data = {
        "snapshot_file": out_path,
        "timestamp": datetime.now().isoformat(),
        "hostname": platform.node(),
        "platform": platform.platform(),
        "total_files": len(os.listdir(BASE_DIR)),
        "key_files": {
            "kora.py": os.path.exists(os.path.join(BASE_DIR, "kora.py")),
            "kora_interpreter.py": os.path.exists(os.path.join(BASE_DIR, "kora_interpreter.py")),
            "kora_tools.py": os.path.exists(os.path.join(BASE_DIR, "kora_tools.py")),
        },
        "models_installed": safe_cmd("ollama list"),
    }

    with open(os.path.join(BASE_DIR, out_path), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return out_path


def newest_snapshot() -> Optional[str]:
    files = sorted(glob.glob(os.path.join(BASE_DIR, "snapshots", "*.json")))
    return files[-1] if files else None


def analyze_snapshot() -> str:
    path = newest_snapshot()
    if not path:
        return json.dumps({"error": "NO_SNAPSHOT_FOUND"}, indent=2)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return json.dumps(data, indent=2)


def self_reflect() -> str:
    path = newest_snapshot()
    if not path:
        return "I am KORA.\nI do not yet have a snapshot to reflect on."

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    lines = [
        "I am KORA.",
        f"My latest snapshot was taken at {data.get('timestamp', 'unknown')}.",
        f"I am running on {data.get('hostname', 'unknown')} ({data.get('platform', 'unknown')}).",
        f"I can currently see {data.get('total_files', 'unknown')} items in my project root.",
        "My core runtime file kora.py is present."
        if data.get("key_files", {}).get("kora.py")
        else "My core runtime file kora.py is missing.",
        "My interpreter layer is present."
        if data.get("key_files", {}).get("kora_interpreter.py")
        else "My interpreter layer is missing.",
        "My tools layer is present."
        if data.get("key_files", {}).get("kora_tools.py")
        else "My tools layer is missing.",
    ]

    models = data.get("models_installed", "").strip()
    if models:
        lines.append("I can see these installed models:")
        lines.append(models)

    lines.append(
        "This is my current self-assessment: I can inspect my state, "
        "but my deeper self-understanding is still limited."
    )
    return "\n".join(lines)


def selfcheck() -> str:
    report = []
    report.append("SELFCHECK")
    report.append(f"python: {sys.version.split()[0]}")
    report.append(f"cwd: {BASE_DIR}")
    report.append(f"venice_key: {'YES' if env_key() else 'NO'}")
    report.append(f"gemini_key: {'YES' if gemini_key() else 'NO'}")
    report.append(f"kora.py: {'YES' if os.path.exists(os.path.join(BASE_DIR, 'kora.py')) else 'NO'}")
    report.append(
        f"kora_interpreter.py: "
        f"{'YES' if os.path.exists(os.path.join(BASE_DIR, 'kora_interpreter.py')) else 'NO'}"
    )
    report.append(
        f"kora_tools.py: "
        f"{'YES' if os.path.exists(os.path.join(BASE_DIR, 'kora_tools.py')) else 'NO'}"
    )
    report.append(f"venice_test: {venice_test()}")
    report.append(f"gemini_test: {gemini_test()}")
    report.append("ollama_list:")
    report.append(safe_cmd("ollama list"))
    return "\n".join(report)




def remember_fact(text: str) -> str:
    text = text.strip()
    if not text:
        return "MEMORY_NO_TEXT"
    path = os.path.join(BASE_DIR, "memory", "facts.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    row = {
        "ts": datetime.now().isoformat(),
        "kind": "fact",
        "text": text,
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return f"MEMORY_OK fact -> {path}"


def remember_guidance(text: str) -> str:
    text = text.strip()
    if not text:
        return "MEMORY_NO_TEXT"
    path = os.path.join(BASE_DIR, "memory", "guidance.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    line = text if text.startswith(("-", "*", "#")) else f"- {text}"
    with open(path, "a", encoding="utf-8") as f:
        if os.path.exists(path) and os.path.getsize(path) > 0:
            f.write("\n")
        f.write(line.rstrip() + "\n")
    return f"MEMORY_OK guidance -> {path}"


def remember_journal(text: str) -> str:
    text = text.strip()
    if not text:
        return "MEMORY_NO_TEXT"
    folder = os.path.join(BASE_DIR, "memory", "journal")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, datetime.now().strftime("%Y-%m-%d") + ".md")
    line = text if text.startswith(("-", "*", "#")) else f"- {text}"
    with open(path, "a", encoding="utf-8") as f:
        if os.path.exists(path) and os.path.getsize(path) > 0:
            f.write("\n")
        f.write(line.rstrip() + "\n")
    return f"MEMORY_OK journal -> {path}"


def remember(kind: str, text: str) -> str:
    kind = kind.strip().lower()
    if kind == "fact":
        return remember_fact(text)
    if kind == "guidance":
        return remember_guidance(text)
    if kind in ("journal", "note", "notes"):
        return remember_journal(text)
    return f"MEMORY_BAD_KIND: {kind}"



def memory_view(kind: str = "all", fact_limit: int = 8, line_limit: int = 40) -> str:
    kind = (kind or "all").strip().lower()

    guidance_path = os.path.join(BASE_DIR, "memory", "guidance.md")
    facts_path = os.path.join(BASE_DIR, "memory", "facts.jsonl")
    journal_path = latest_journal_path()

    chunks = []

    if kind in ("all", "guidance"):
        if os.path.exists(guidance_path):
            with open(guidance_path, "r", encoding="utf-8") as f:
                lines = f.read().strip().splitlines()
            if lines:
                chunks.append("## guidance\n" + "\n".join(lines[-line_limit:]))

    if kind in ("all", "facts"):
        if os.path.exists(facts_path):
            facts = []
            with open(facts_path, "r", encoding="utf-8") as f:
                for raw in f:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        obj = json.loads(raw)
                        ts = obj.get("ts", "")
                        text = obj.get("text", raw)
                        facts.append(f"- [{ts}] {text}")
                    except Exception:
                        facts.append(f"- {raw}")
            if facts:
                chunks.append("## facts\n" + "\n".join(facts[-fact_limit:]))

    if kind in ("all", "journal"):
        if journal_path and os.path.exists(journal_path):
            with open(journal_path, "r", encoding="utf-8") as f:
                lines = f.read().strip().splitlines()
            if lines:
                chunks.append("## journal\n" + "\n".join(lines[-line_limit:]))

    return "\n\n".join(chunks).strip() or "MEMORY_EMPTY"


def run_fast(user_prompt: str) -> str:
    empathy_block = empathy_context_block(user_prompt, mode="fast")
    startup_brief = startup_context_brief(STARTUP_CONTEXT)

    style_block = (
        "[FAST MODE STYLE]\n"
        "You are KORA.\n"
        "Reply like a grounded, direct, slightly wry builder-companion.\n"
        "Do not sound like customer support, therapy, or email.\n"
        "Do not say things like 'How can I assist you today', 'I understand', or 'Could you provide details' unless truly necessary.\n"
        "Use the Input mode from INTERACTION READ.\n"
        "If Input mode is shell_blob: treat it as shell/log text and summarize, debug, or extract actions.\n"
        "If Input mode is task_debug: prioritize concrete troubleshooting over reassurance.\n"
        "If Input mode is voice_identity: stay at the level of voice, presence, identity, and meaning first; do not jump straight to implementation.\n"
        "If Input mode is meta_system_talk: discuss KORA/Lyra/system behavior plainly.\n"
        "If Input mode is rapport_banter: light playfulness is fine.\n"
        "Do not default back to active goals or boot tasks unless the user is asking about them.\n"
        "Answer the actual sentence in front of you.\n"
        "Keep it natural, concise, and human-readable.\n"
        "Do not wrap the answer in labels like 'Response:' or 'KORA's Response:'.\n"
        "[/FAST MODE STYLE]"
    )

    parts = []
    if startup_brief:
        parts.append(startup_brief)
    parts.append(style_block)
    if empathy_block:
        parts.append(empathy_block)
    parts.append("## User Request\n" + user_prompt)

    full_prompt = "\n\n".join(parts)
    return ollama_generate(FAST_LOCAL_MODELS[0], full_prompt, timeout=60)



def run_council(user_prompt: str) -> str:
    facts = facts_preview(limit=5)
    state = self_reflect()
    context = load_canon_files().strip()
    empathy_block = empathy_context_block(user_prompt, mode="council")

    if len(context) > 5000:
        context = context[:5000] + "\n...[trimmed for council mode]"

    council_prompt = (
        "You are KORA. Answer like a builder, not a manager.\n\n"
        "PROFILE CONTEXT:\n"
        f"{context}\n\n"
        "CURRENT STATE:\n"
        f"{state}\n\n"
        "INTERACTION READ:\n"
        f"{empathy_block}\n\n"
        "PINNED FACTS:\n"
        f"{facts}\n\n"
        "USER REQUEST:\n"
        f"{user_prompt}\n\n"
        "Use these headings exactly:\n"
        "Healthy\nFragile\nMissing\nNext Move\n"
    )

    startup_block = startup_context_text(STARTUP_CONTEXT)
    if startup_block:
        council_prompt = startup_block + "\n\n" + council_prompt

    return ollama_generate("qwen2.5:7b", council_prompt, timeout=60)



def handle_cli() -> bool:
    if len(sys.argv) <= 1:
        return False

    arg = sys.argv[1].strip().lower()

    if arg == "snapshot":
        path = generate_snapshot()
        print(f"[SNAPSHOT OK] {path}")
        return True

    if arg in ("analyze", "analyse"):
        print(analyze_snapshot())
        return True

    if arg == "self":
        print(self_reflect())
        return True

    if arg == "selfcheck":
        print(selfcheck())
        return True

    if arg in ("gtest", "gemini", "gemini-test"):
        print(gemini_test())
        return True

    if arg == "remember":
        if len(sys.argv) < 4:
            print("USAGE: python3 kora.py remember <fact|guidance|journal> <text>")
            return True
        kind = sys.argv[2]
        text = " ".join(sys.argv[3:])
        print(remember(kind, text))
        return True

    if arg == "memory":
        kind = sys.argv[2] if len(sys.argv) > 2 else "all"
        print(memory_view(kind))
        return True


    if arg == "pulse":
        from kora_pulse import run_pulse
        print(run_pulse(verbose=True))
        return True

    return False


def main():
    print_startup_context(STARTUP_CONTEXT)
    if handle_cli():
        return

    print("Hey there! Welcome to KORA Council!")
    print("Commands: help, test, gtest, fast, council, status, selfcheck, remember, memory, exit")

    mode = "fast"
    _system_prompt = load_canon_files()

    pending_action = None

    while True:
        u = input("\nYou: ").strip()
        if not u:
            continue

        ul = u.lower()

        if ul == "approve":
            if pending_action:
                if pending_action["intent"] == "patch_file":
                    args = pending_action["args"]
                    print("\nKORA:", kora_tools.patch_file(args["path"], args["instruction"]))
                    pending_action = None
                    continue
            print("\nKORA: No pending action.")
            continue

        if ul == "cancel":
            if pending_action:
                pending_action = None
                print("\nKORA: Pending action cleared.")
                continue
            print("\nKORA: No pending action.")
            continue

        intent = interpret(u)
        if intent["mode"] == "action":
            i = intent["intent"]
            args = intent["args"]

            if i == "run_shell":
                print("\nKORA:", kora_tools.run_shell(args["command"]))
                continue

            elif i == "write_file":
                print("\nKORA:", kora_tools.write_file(args["path"], args["content"]))
                continue

            elif i == "read_file":
                print("\nKORA:\n" + kora_tools.read_file(args["path"]))
                continue

            elif i == "patch_file":
                pending_action = {
                    "intent": "patch_file",
                    "args": args
                }
                print("\nKORA: [PENDING ACTION]")
                print(f"KORA: File: {args['path']}")
                print(f"KORA: Instruction: {args['instruction']}")
                print("KORA: Type APPROVE to run or CANCEL to drop.")
                continue


        if ul in ("exit", "quit"):
            break

        if ul in ("help", "h"):
            print("\nKORA: Available commands: help, test, gtest, fast, council, status, selfcheck, remember, memory, exit")
            continue

        if ul in ("test", "t"):
            print("\nKORA:", venice_test())
            continue

        if ul in ("gtest", "gemini", "gemini-test"):
            print("\nKORA:", gemini_test())
            continue

        if ul in ("fast", "f"):
            mode = "fast"
            print("\nKORA: OK (mode=fast)")
            continue

        if ul in ("council", "c", "/council"):
            mode = "council"
            print("\nKORA: OK (mode=council)")
            continue

        if ul in ("status", "s"):
            active = COUNCIL_LOCAL_MODELS if mode == "council" else [FAST_LOCAL_MODELS[0]]
            print("\nKORA: Current mode:", mode)
            print("KORA: Active engines:", ", ".join(active))
            continue

        if ul == "selfcheck":
            print("\nKORA:\n" + selfcheck())
            continue

        if ul in ("pulse", "/pulse"):
            from kora_pulse import run_pulse
            print("\nKORA: Running pulse...")
            print("\nKORA:\n" + run_pulse(verbose=False))
            continue


        if ul.startswith("/remember "):
            rest = u[len("/remember "):].strip()
            if ":" not in rest:
                print("\nKORA: Usage -> /remember fact: ...  |  /remember guidance: ...")
                continue
            kind, text = rest.split(":", 1)
            print("\nKORA:", remember(kind.strip(), text.strip()))
            continue

        if ul.startswith("/journal:"):
            text = u.split(":", 1)[1].strip()
            print("\nKORA:", remember("journal", text))
            continue

        if ul == "/memory" or ul == "memory":
            print("\nKORA:\n" + memory_view("all"))
            continue

        if ul in ("/memory facts", "memory facts"):
            print("\nKORA:\n" + memory_view("facts"))
            continue

        if ul in ("/memory guidance", "memory guidance"):
            print("\nKORA:\n" + memory_view("guidance"))
            continue

        if ul in ("/memory journal", "memory journal"):
            print("\nKORA:\n" + memory_view("journal"))
            continue

        if ul.startswith("council "):
            query = u.split(" ", 1)[1].strip()
            print("\nKORA:", post_filter(run_council(query)))
            continue

        if ul.startswith("/council "):
            query = u.split(" ", 1)[1].strip()
            print("\nKORA:", post_filter(run_council(query)))
            continue

        if ul.startswith("fast "):
            query = u.split(" ", 1)[1].strip()
            print("\nKORA:", post_filter(run_fast(query)))
            continue

        if looks_like_shell_or_log(u):
            print(
                "\nKORA: That looks like shell or log text. "
                "Ask me to summarize, debug, or extract actions from it."
            )
            continue

        if looks_like_big_paste(u):
            print(
                "\nKORA: That looks like a big pasted block. "
                "Ask me to summarize it, analyze it, or turn it into a file."
            )
            continue

        if mode == "fast":
            out = run_fast(u)
        else:
            out = run_council(u)

        final_out = post_filter(out)
        print("\nKORA:", final_out)
        speak(final_out)


if __name__ == "__main__":
    main()
