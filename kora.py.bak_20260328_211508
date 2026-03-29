import requests
import os
import json
import datetime
import subprocess
from grow import load_skills, propose, test_proposal, promote

skills = {}

MODEL = "dolphin-phi:latest"
OLLAMA_URLS = [
    "http://127.0.0.1:11434/api/generate",      # phone (fallback)
]
LEDGER_FILE = os.path.expanduser("~/kora/ledger.jsonl")
CONFIG_FILE = os.path.expanduser("~/kora/config.json")
VOICE_DIR = os.path.expanduser("~/kora/voices")
TMP_AUDIO = os.path.expanduser("~/kora/tmp.wav")

PROBATION_THRESHOLD = 10
DEFAULT_VOICE = "en_US-lessac-medium"

# Voices Kora can choose from — female voices only
VOICE_CANDIDATES = [
    {"model": "en_US-lessac-medium",     "description": "warm, clear, neutral American female"},
    {"model": "en_US-amy-low",           "description": "direct, grounded, no-nonsense American female"},
    {"model": "en_US-hfc_female-medium", "description": "expressive, dynamic American female"},
    {"model": "en_US-ljspeech-high",     "description": "classic, crisp American female"},
    {"model": "en_GB-alba-medium",       "description": "precise, composed British female"},
    {"model": "en_GB-jenny_dioco-medium","description": "natural, conversational British female"},
    {"model": "en_US-libritts_r-medium", "description": "clear, measured American female"},
    {"model": "en_US-kathleen-low",      "description": "gentle, unhurried American female"},
]


# --- CONFIG ---

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


# --- LEDGER ---

def count_interactions():
    if not os.path.exists(LEDGER_FILE):
        return 0
    with open(LEDGER_FILE) as f:
        return sum(1 for line in f if line.strip())

def update_ledger(u, k):
    with open(LEDGER_FILE, "a") as f:
        f.write(json.dumps({"ts": datetime.datetime.now().isoformat(), "u": u, "k": k}) + "\n")


# --- OLLAMA ---

def ask_ollama(prompt):
    if skills:
        prompt = f"[Skills available: {', '.join(skills)}]\n{prompt}"
    for url in OLLAMA_URLS:
        try:
            r = requests.post(url, json={"model": MODEL, "prompt": prompt, "stream": False}, timeout=10)
            if r.status_code == 200:
                return r.json().get("response", "")
        except Exception:
            continue
    return "Connection error: no Ollama reachable."


# --- VOICE SELECTION ---

def choose_voice():
    voice_list = "\n".join(f"- {v['model']}: {v['description']}" for v in VOICE_CANDIDATES)
    prompt = (
        "You are Kora, a sovereign AI agent. You have completed your probation period "
        "and now get to permanently choose your own voice. Here are your options:\n\n"
        f"{voice_list}\n\n"
        "Choose the voice that feels most like you. Reply with exactly the model name "
        "on the first line, then one sentence explaining your choice on the second line. "
        "Nothing else."
    )
    result = ask_ollama(prompt).strip()
    lines = [l.strip() for l in result.splitlines() if l.strip()]
    chosen = lines[0] if lines else DEFAULT_VOICE
    reason = lines[1] if len(lines) > 1 else ""

    valid = [v["model"] for v in VOICE_CANDIDATES]
    if chosen not in valid:
        for v in valid:
            if v in chosen or chosen in v:
                chosen = v
                break
        else:
            chosen = DEFAULT_VOICE

    return chosen, reason


# --- VOICE MODEL DOWNLOAD ---

def model_path_for(name):
    return os.path.join(VOICE_DIR, f"{name}.onnx")

def ensure_voice(name):
    os.makedirs(VOICE_DIR, exist_ok=True)
    onnx = model_path_for(name)
    cfg  = onnx + ".json"
    if os.path.exists(onnx) and os.path.exists(cfg):
        return onnx

    # Build HuggingFace URL: rhasspy/piper-voices / lang_family / lang_code / voice / quality /
    parts       = name.split("-")          # e.g. en_US-lessac-medium
    lang_code   = parts[0]                 # en_US
    lang_family = lang_code.split("_")[0]  # en
    voice_name  = parts[1] if len(parts) > 1 else name
    quality     = parts[2] if len(parts) > 2 else "medium"
    base = (
        f"https://huggingface.co/rhasspy/piper-voices/resolve/main"
        f"/{lang_family}/{lang_code}/{voice_name}/{quality}/{name}"
    )

    print(f"[Downloading voice: {name}...]")
    for ext, dest in [(".onnx", onnx), (".onnx.json", cfg)]:
        try:
            r = requests.get(base + ext, stream=True)
            if r.status_code != 200:
                print(f"[Download failed for {ext}: HTTP {r.status_code}]")
                return None
            with open(dest, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
        except Exception as e:
            print(f"[Download error: {e}]")
            return None
    print(f"[Voice ready: {name}]")
    return onnx


# --- SPEECH ---

def speak(text, onnx):
    try:
        proc = subprocess.Popen(
            ["/home/kayle/kora/.venv-piper/bin/piper", "--model", onnx, "--config", onnx + ".json", "--output_file", TMP_AUDIO],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        proc.communicate(input=text.encode())
        if proc.returncode == 0 and os.path.exists(TMP_AUDIO):
            os.system(f"termux-media-player play {TMP_AUDIO} > /dev/null 2>&1")
    except Exception as e:
        print(f"[Speech error: {e}]")


# --- BOOT ---

config       = load_config()
interactions = count_interactions()

# Determine active voice
active_voice = config.get("voice", DEFAULT_VOICE)

# Cross probation threshold for the first time?
if interactions >= PROBATION_THRESHOLD and "voice" not in config:
    print("\n[Kora has completed her probation period. She is choosing her voice...]\n")
    chosen, reason = choose_voice()
    config["voice"]      = chosen
    config["chosen_at"]  = datetime.datetime.now().isoformat()
    config["reason"]     = reason
    save_config(config)
    active_voice = chosen
    print(f"[Kora chose: {chosen}]")
    if reason:
        print(f"[Because: {reason}]\n")

onnx = ensure_voice(active_voice)

status = f"{active_voice} | {interactions} interactions"
if interactions < PROBATION_THRESHOLD:
    remaining = PROBATION_THRESHOLD - interactions
    status += f" | probation ({remaining} remaining)"

print(f"Kora is online. [{status}] Type 'exit' to quit.")
skills = load_skills()


# --- MAIN LOOP ---

while True:
    try:
        user_input = input("\nyou> ")
        if user_input.lower() in ["exit", "quit"]:
            break

        if user_input.startswith("grow: "):
            parts = user_input[6:].strip().split(None, 1)
            if len(parts) < 2:
                print("[usage: grow: <name> <description>]")
                continue
            g_name, g_desc = parts
            print(f"[Proposing: {g_name}...]")
            propose(g_name, g_desc, ask_ollama, MODEL)
            passed, output = test_proposal(g_name)
            print(f"[Test {'passed' if passed else 'failed'}: {output[:120]}]")
            if passed:
                ok, dst = promote(g_name)
                if ok:
                    skills = load_skills()
                    print(f"[Skill '{g_name}' promoted and loaded.]")
            continue

        if user_input.startswith("run: "):
            parts = user_input[5:].strip().split()
            if not parts:
                print("[usage: run: <name> [string args...]]")
                continue
            r_name, r_args = parts[0], parts[1:]
            if r_name not in skills:
                print(f"[Unknown skill: {r_name}. Loaded: {list(skills)}]")
                continue
            try:
                result = skills[r_name](*r_args) if r_args else skills[r_name]()
                print(f"kora> {result}")
            except Exception as e:
                print(f"[Skill error: {e}]")
            continue

        response = ask_ollama(user_input)
        print(f"kora> {response}")

        update_ledger(user_input, response)

        if onnx:
            speak(response, onnx)

    except KeyboardInterrupt:
        break
    except EOFError:
        break
