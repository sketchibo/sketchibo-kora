import subprocess, os, json, re, urllib.request, urllib.parse
import requests
from pathlib import Path

BASE_DIR = Path(__file__).parent

def tor_fetch(url, timeout=30):
    """Fetch a URL through Tor. Works on clearnet and .onion sites."""
    try:
        result = subprocess.run(
            ['torsocks', 'curl', '-s', '--max-time', str(timeout), '-L', url],
            capture_output=True, text=True, timeout=timeout+5
        )
        out = result.stdout.strip()
        if not out:
            return f"Empty response (stderr: {result.stderr[:200]})"
        # Strip HTML tags for readability
        import re as _re
        out = _re.sub(r'<[^>]+>', ' ', out)
        out = _re.sub(r'\s+', ' ', out).strip()
        return out[:3000]
    except Exception as e:
        return f"tor_fetch error: {e}"

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
        # Kora's voice: en-US female, pitch 1.1, rate 1.0
        subprocess.Popen([
            'termux-tts-speak',
            '-l', 'en', '-n', 'US',
            '-p', '1.1',
            '-r', '0.85',
            text
        ])
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

def remember_fact(text, source='kora'):
    """Append a fact to Kora's persistent memory."""
    try:
        import json
        from datetime import datetime
        facts_path = BASE_DIR / 'memory' / 'facts.jsonl'
        facts_path.parent.mkdir(parents=True, exist_ok=True)
        row = {'ts': datetime.now().isoformat(), 'kind': 'fact', 'source': source, 'text': text}
        with facts_path.open('a', encoding='utf-8') as f:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
        return f'fact saved: {text[:60]}'
    except Exception as e:
        return f'ERROR: {e}'

def lce_log(entry_type, content, context=''):
    """Log a life compression entry — lived experience, intention, outcome, or thought."""
    try:
        import json
        from datetime import datetime
        lce_path = BASE_DIR / 'memory' / 'lce_ledger.jsonl'
        lce_path.parent.mkdir(parents=True, exist_ok=True)
        row = {'ts': datetime.now().isoformat(), 'type': entry_type, 'content': content, 'context': context}
        with lce_path.open('a', encoding='utf-8') as f:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
        return f'lce entry logged: [{entry_type}] {content[:60]}'
    except Exception as e:
        return f'ERROR: {e}'

def take_snapshot():
    """Dump Kora's current state — models, memory, files — as a JSON snapshot."""
    try:
        import json
        snap = {
            'ts': __import__('datetime').datetime.now().isoformat(),
            'ollama_models': subprocess.run(['ollama', 'list'], capture_output=True, text=True).stdout.strip(),
            'memory_files': [str(p) for p in (BASE_DIR / 'memory').glob('*') if p.is_file()],
            'facts_count': sum(1 for _ in open(BASE_DIR / 'memory' / 'facts.jsonl')) if (BASE_DIR / 'memory' / 'facts.jsonl').exists() else 0,
            'uptime': subprocess.run(['uptime'], capture_output=True, text=True).stdout.strip(),
        }
        return json.dumps(snap, indent=2)
    except Exception as e:
        return f'ERROR: {e}'

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

def get_signals():
    """Pull trading signals from all sources: whale moves, 4chan /biz/, Reddit, CoinGecko."""
    try:
        from kora_signals import get_all_signals, print_report
        ranked, raw = get_all_signals(verbose=False)
        lines = ["=== SIGNAL REPORT ==="]
        lines.append("TOP BULLISH:")
        for sym, score in ranked[:5]:
            if score > 0:
                sources = list(set(s["source"] for s in raw if s.get("symbol") == sym and "error" not in s))
                lines.append(f"  {sym}: score={score:+d} [{', '.join(sources)}]")
        lines.append("TOP BEARISH:")
        for sym, score in ranked[-3:]:
            if score < 0:
                lines.append(f"  {sym}: score={score:+d}")
        return "\n".join(lines)
    except Exception as e:
        return f"Signal error: {e}"


def portfolio_snapshot():
    """Get current Kraken portfolio value and save a snapshot."""
    try:
        result = subprocess.run(
            ["python3", str(BASE_DIR / "kora_snapshot_tracker.py")],
            capture_output=True, text=True, timeout=30, cwd=str(BASE_DIR)
        )
        return result.stdout.strip() or result.stderr.strip()
    except Exception as e:
        return f"Snapshot error: {e}"
