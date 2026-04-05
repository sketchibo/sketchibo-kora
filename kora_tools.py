import subprocess, os, json, re, urllib.request, urllib.parse
import requests
from pathlib import Path

BASE_DIR = Path(__file__).parent

# ── ADB ──────────────────────────────────────────────────────────────────
BOX_IP = "192.168.1.211:5555"

def adb(command):
    """Run a single ADB shell command on Telus box. For sequences use run_shell."""
    try:
        # If it looks like a shell command (starts with 'shell'), extract and run properly
        if command.strip().startswith('shell '):
            shell_cmd = command.strip()[6:]
            result = subprocess.run(
                ['adb', '-s', BOX_IP, 'shell', shell_cmd],
                capture_output=True, text=True, timeout=15)
        else:
            result = subprocess.run(f"adb -s {BOX_IP} {command}",
                shell=True, capture_output=True, text=True, timeout=15)
        return result.stdout.strip() or result.stderr.strip() or '(ok)'
    except Exception as e:
        return f"ADB ERROR: {e}"

def adb_tap(x, y):
    return adb(f"shell input tap {x} {y}")

def adb_key(keycode):
    return adb(f"shell input keyevent {keycode}")

def tv_screenshot():
    try:
        subprocess.run(f"adb -s {BOX_IP} shell screencap -p /sdcard/kora_screen.png",
            shell=True, timeout=10)
        out = BASE_DIR / 'vision'
        out.mkdir(exist_ok=True)
        subprocess.run(f"adb -s {BOX_IP} pull /sdcard/kora_screen.png {out}/tv_latest.png",
            shell=True, timeout=10)
        return f"Screenshot saved to {out}/tv_latest.png"
    except Exception as e:
        return f"ERROR: {e}"

# ── WEB SEARCH ───────────────────────────────────────────────────────────
def web_search(query, n=5):
    # Try DuckDuckGo first
    try:
        q = urllib.parse.quote(query)
        req = urllib.request.Request(
            f"https://html.duckduckgo.com/html/?q={q}",
            headers={'User-Agent': 'Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36'})
        html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8', errors='ignore')
        results = re.findall(r'<a class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>', html)
        out = [f"- {t.strip()}: {h}" for h, t in results[:n]]
        if out:
            return '\n'.join(out)
    except Exception:
        pass

    # Fallback: Gemini search grounding
    try:
        key = os.getenv('GOOGLE_API_KEY', '')
        if key:
            url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}'
            body = {
                'contents': [{'role': 'user', 'parts': [{'text': f'Search the web and summarize: {query}. Give {n} key results as bullet points with sources.'}]}],
                'generationConfig': {'maxOutputTokens': 500}
            }
            r = requests.post(url, json=body, timeout=30)
            if r.status_code == 200:
                return r.json()['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"Search error: {e}"

    return "Search unavailable — no working backend."

# ── TTS ──────────────────────────────────────────────────────────────────
def speak(text):
    try:
        pipe = os.path.expanduser('~/.tts_pipe')
        if os.path.exists(pipe):
            with open(pipe, 'w') as f: f.write(text)
            return '(speaking)'
        subprocess.Popen(['bash', os.path.expanduser('~/scripts/speak.sh'), text])
        return '(speaking)'
    except Exception as e:
        return f"TTS error: {e}"

# ── TASK QUEUE ───────────────────────────────────────────────────────────
def queue_task(title, command=None, note=None):
    try:
        import sys; sys.path.insert(0, str(BASE_DIR))
        from core.task_runner import add_task
        tid = add_task(title, command=command, note=note)
        return f"Task queued [{tid}]: {title}"
    except Exception as e:
        return f"ERROR: {e}"

def task_status():
    try:
        import sys; sys.path.insert(0, str(BASE_DIR))
        from core.task_runner import status_summary
        return status_summary()
    except Exception as e:
        return f"ERROR: {e}"

def run_shell(command):
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True
        )
        out = (result.stdout or "").strip()
        err = (result.stderr or "").strip()
        if out:
            return out
        if err:
            return err
        return "(no output)"
    except Exception as e:
        return f"ERROR: {e}"

def write_file(path, content):
    try:
        import os
        if not os.path.isabs(path):
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"File written: {path}"
    except Exception as e:
        return f"ERROR: {e}"

def read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"ERROR: {e}"

def patch_file(path, instruction):
    return f"[PATCH REQUEST]\\nFile: {path}\\nInstruction: {instruction}"

# ── KRAKEN TRADING MODULE ───────────────────────────────────────────────
# Auto-generated by handoff script. 
# Provides KORA with the ability to call: kraken_trade("buy", "XBTUSD", 0.5, 60000)
# ─────────────────────────────────────────────────────────────────────────
import subprocess
import os

def kraken_trade(action: str, pair: str, amount: float, price: float = None):
    """
    Executes a trade via the Kraken CLI.
    
    Parameters:
    - action: "buy" or "sell"
    - pair: e.g., "XBTUSD" (Bitcoin) or "ETHUSD"
    - amount: Quantity to trade
    - price: Limit price (optional. If not provided, executes market order)
    """
    # Ensure Kraken CLI is installed
    if not os.path.exists("/usr/local/bin/kraken"):
        print("[KORA] Installing Kraken CLI...")
        try:
            subprocess.run(
                ["curl", "--proto", "=https", "--tlsv1.2", "-LsSf", 
                 "https://github.com/krakenfx/kraken-cli/releases/latest/download/kraken-cli-installer.sh", 
                 "|", "sh"], shell=True, check=True, timeout=120
            )
        except Exception as e:
            return f"[ERROR] Installation failed: {e}"

    # Construct Command
    cmd = ["kraken", "order"]
    
    if price:
        # Limit Order
        cmd.extend([action, str(price), str(amount), pair])
    else:
        # Market Order
        cmd.extend([action, str(amount), pair])
        
    # Execute
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            print(f"[KORA] Kraken Error: {result.stderr}")
            return f"[ERROR] {result.stderr.strip()}"
        else:
            print(f"[KORA] Trade Executed: {result.stdout}")
            return f"[SUCCESS] {result.stdout.strip()}"
            
    except subprocess.TimeoutExpired:
        return "[ERROR] Command timed out."
    except Exception as e:
        return f"[ERROR] {e}"
