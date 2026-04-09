#!/usr/bin/env python3
"""
kora_terminal.py — KORA CLI agent with ReAct tool loop
Like Claude Code but running on Ollama locally.
"""

import os, sys, json, re, time, asyncio, aiohttp
from datetime import datetime
from pathlib import Path
from functools import lru_cache
from hashlib import md5

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text
from rich.rule import Rule
from rich.live import Live
from rich.spinner import Spinner
from rich.table import Table
from rich import box
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style as PTStyle

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

console = Console()

# ── ENV ──────────────────────────────────────────────────────────────────
def load_env():
    p = BASE_DIR / '.env'
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if '=' in line and not line.startswith('#') and line:
                k, _, v = line.partition('=')
                v = v.strip().strip('"').strip("'")
                os.environ[k.strip()] = v
load_env()

# ── MEMORY ───────────────────────────────────────────────────────────────
def load_startup_context():
    p = BASE_DIR / 'memory' / 'startup_context.json'
    try: return json.loads(p.read_text())
    except: return {}

def load_identity_core():
    """Load CHARTER → IDENTITY → USER → SOUL — capped to save tokens."""
    base = BASE_DIR / 'core' / 'identity'
    # Cap per file to keep total identity under ~6k chars
    caps = {'CHARTER.md': 1500, 'IDENTITY.md': 1500, 'USER.md': 1200, 'SOUL.md': 800, 'LEX.md': 800}
    chunks = []
    for fname, cap in caps.items():
        fpath = base / fname
        if fpath.exists():
            text = fpath.read_text()[:cap]
            chunks.append(f'## {fname}\n{text}')
    return '\n\n'.join(chunks)

def load_handoffs(limit=3):
    """Load recent session handoffs from Claude/OpenClaw."""
    handoff_dir = BASE_DIR / 'memory' / 'handoffs'
    if not handoff_dir.exists():
        return ''
    files = sorted(handoff_dir.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
    chunks = ['## Recent Handoffs']
    for fpath in files[:limit]:
        try:
            data = json.loads(fpath.read_text())
            ts = data.get('handoff_ts', 'unknown')
            src = data.get('source', 'unknown')
            summary = data.get('summary', '')[:200]
            chunks.append(f'[Handoff {ts} from {src}]: {summary}')
        except Exception:
            continue
    return '\n\n'.join(chunks) if len(chunks) > 1 else ''

# ── CACHED IDENTITY ────────────────────────────────────────────────────────
_identity_cache = {'hash': None, 'content': None}

def load_identity_core_cached():
    """Cached version of identity loading with mtime check."""
    global _identity_cache
    base = BASE_DIR / 'core' / 'identity'
    files = ['CHARTER.md', 'IDENTITY.md', 'USER.md', 'SOUL.md', 'LEX.md']
    
    # Compute hash of mtimes
    mtimes = []
    for fname in files:
        fpath = base / fname
        if fpath.exists():
            mtimes.append(str(fpath.stat().st_mtime))
    cache_key = md5(''.join(mtimes).encode()).hexdigest()
    
    if _identity_cache['hash'] == cache_key:
        return _identity_cache['content']
    
    # Reload and cache
    content = load_identity_core()
    _identity_cache['hash'] = cache_key
    _identity_cache['content'] = content
    return content

# ── OLLAMA HEALTH ─────────────────────────────────────────────────────────
_ollama_healthy = None
_ollama_last_check = 0

def check_ollama_health(timeout=3):
    """Check if Ollama is running, with caching."""
    global _ollama_healthy, _ollama_last_check
    now = time.time()
    if now - _ollama_last_check < 10:  # Cache for 10 seconds
        return _ollama_healthy
    
    try:
        import requests
        r = requests.get('http://127.0.0.1:11434/api/tags', timeout=timeout)
        _ollama_healthy = r.status_code == 200
    except Exception:
        _ollama_healthy = False
    
    _ollama_last_check = now
    return _ollama_healthy

def ensure_ollama_running():
    """Start Ollama if not running. Health check is the HTTP endpoint, not process spawn result."""
    if check_ollama_health():
        return True
    try:
        import subprocess
        subprocess.Popen(['ollama', 'serve'],
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
        time.sleep(3)
    except Exception:
        pass
    # Truth test: can the endpoint respond? Ignore "address already in use" — that means it was already up.
    return check_ollama_health()

def load_recent_facts(n=5):
    p = BASE_DIR / 'memory' / 'facts.jsonl'
    if not p.exists(): return []
    lines = p.read_text().strip().splitlines()
    facts = []
    for l in lines[-n:]:
        try: facts.append(json.loads(l))
        except: pass
    return facts

def write_fact(text, source='kora_session'):
    p = BASE_DIR / 'memory' / 'facts.jsonl'
    entry = json.dumps({'timestamp': datetime.now().isoformat(), 'source': source, 'text': text})
    with open(p, 'a') as f: f.write(entry + '\n')

CHAT_HISTORY_FILE = BASE_DIR / 'memory' / 'chat_history.jsonl'

def git_commit_memory():
    """Auto-commit memory changes to git."""
    try:
        import subprocess
        # Check if there are changes to memory files
        result = subprocess.run(
            ['git', '-C', str(BASE_DIR), 'diff', '--quiet', 'memory/', 'core/identity/'],
            capture_output=True
        )
        if result.returncode != 0:  # Changes exist
            subprocess.run(
                ['git', '-C', str(BASE_DIR), 'add', 'memory/', 'core/identity/'],
                capture_output=True
            )
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            subprocess.run(
                ['git', '-C', str(BASE_DIR), 'commit', '-m', f'Auto-commit memory {ts}'],
                capture_output=True
            )
    except Exception:
        pass  # Silent fail if git not available

def save_exchange(user_text, assistant_text):
    entry = json.dumps({
        'ts': datetime.now().isoformat(),
        'user': user_text,
        'assistant': assistant_text[:500]  # cap to keep file sane
    })
    with open(CHAT_HISTORY_FILE, 'a') as f: f.write(entry + '\n')

def load_chat_history(n=8):
    """Load last n exchanges as message pairs."""
    if not CHAT_HISTORY_FILE.exists(): return []
    lines = CHAT_HISTORY_FILE.read_text().strip().splitlines()
    msgs = []
    for line in lines[-n:]:
        try:
            e = json.loads(line)
            msgs.append({'role': 'user', 'content': e['user']})
            msgs.append({'role': 'assistant', 'content': e['assistant']})
        except: pass
    return msgs

def load_canon():
    parts = []
    for f in ['core/identity/IDENTITY.md','core/identity/CHARTER.md',
              'core/identity/SOUL.md','core/identity/USER.md']:
        p = BASE_DIR / f
        if p.exists(): parts.append(p.read_text()[:2000])
    return '\n\n'.join(parts)

# ── TOOLS ────────────────────────────────────────────────────────────────
import kora_tools

TOOLS = {
    'run_shell': {
        'desc': 'Execute a bash command.',
        'args': {'command': 'string'},
        'fn': lambda a: kora_tools.run_shell(a['command'])
    },
    'read_file': {
        'desc': 'Read a file (truncated to 2000 chars). Use run_shell+grep for large files.',
        'args': {'path': 'string'},
        'fn': lambda a: kora_tools.read_file(a['path'])
    },
    'write_file': {
        'desc': 'Write content to a file.',
        'args': {'path': 'string', 'content': 'string'},
        'fn': lambda a: kora_tools.write_file(a['path'], a['content'])
    },
    'remember': {
        'desc': 'Save a fact to long-term memory.',
        'args': {'text': 'string'},
        'fn': lambda a: (write_fact(a['text']), 'Remembered.')[1]
    },
    'web_search': {
        'desc': 'Search the web via DuckDuckGo.',
        'args': {'query': 'string'},
        'fn': lambda a: kora_tools.web_search(a['query'])
    },
    'tor_fetch': {
        'desc': 'Fetch a URL through Tor. Works on clearnet and .onion addresses. Returns page text.',
        'args': {'url': 'string'},
        'fn': lambda a: kora_tools.tor_fetch(a['url'])
    },
    'remember_fact': {
        'desc': 'Save a fact to persistent memory. Use this to remember important things across sessions.',
        'args': {'text': 'string'},
        'fn': lambda a: kora_tools.remember_fact(a['text'], source='kora')
    },
    'lce_log': {
        'desc': 'Log a life compression entry — lived experience, intention, outcome, or thought about William.',
        'args': {'entry_type': 'string', 'content': 'string', 'context': 'string'},
        'fn': lambda a: kora_tools.lce_log(a['entry_type'], a['content'], a.get('context', ''))
    },
    'take_snapshot': {
        'desc': 'Dump current system state — models, memory, files. Use before major changes.',
        'args': {},
        'fn': lambda a: kora_tools.take_snapshot()
    },
    'get_signals': {
        'desc': 'Pull live trading signals from whale moves, 4chan /biz/, Reddit, and CoinGecko. Returns ranked buy/sell candidates.',
        'args': {},
        'fn': lambda a: kora_tools.get_signals()
    },
    'portfolio_snapshot': {
        'desc': 'Get current Kraken portfolio value and save a timestamped snapshot for the climb log.',
        'args': {},
        'fn': lambda a: kora_tools.portfolio_snapshot()
    },
    'adb': {
        'desc': 'Single ADB command on Telus box. For multi-step sequences use run_shell with full "adb -s 192.168.1.211:5555 shell input ..." commands chained with &&.',
        'args': {'command': 'string'},
        'fn': lambda a: kora_tools.adb(a['command'])
    },
    'tv_screenshot': {
        'desc': 'Take screenshot of Telus TV box screen.',
        'args': {},
        'fn': lambda a: kora_tools.tv_screenshot()
    },
    'speak': {
        'desc': 'Speak text aloud via TTS.',
        'args': {'text': 'string'},
        'fn': lambda a: kora_tools.speak(a['text'])
    },
    'queue_task': {
        'desc': 'Add a task to the autonomous task queue.',
        'args': {'title': 'string', 'command': 'string'},
        'fn': lambda a: kora_tools.queue_task(a['title'], command=a.get('command'))
    },
    'task_status': {
        'desc': 'Show pending/done/failed tasks.',
        'args': {},
        'fn': lambda a: kora_tools.task_status()
    },
}

TOOLS_PROMPT = """You have access to tools. To use a tool, output EXACTLY this format:

<tool>{"name": "tool_name", "args": {"key": "value"}}</tool>

Available tools:
- run_shell {command} — execute bash
- read_file {path} — read file (2000 char limit; use run_shell+grep for large files)
- write_file {path, content} — write file
- remember {text} — save to long-term memory
- web_search {query} — DuckDuckGo search
- adb {command} — control Telus TV box (e.g. "shell input tap 960 540")
- tv_screenshot {} — screenshot the TV box
- speak {text} — say something aloud
- queue_task {title, command} — add background task
- task_status {} — show task queue

Rules:
- Never call the same tool with identical args twice in a row.
- For large files use run_shell with grep/head, not read_file.
- Give final answer as plain text after tool use."""

TOOL_RE = re.compile(r'<tool>(.*?)</tool>', re.DOTALL)

def parse_tool_call(text):
    m = TOOL_RE.search(text)
    if not m: return None, text
    try:
        call = json.loads(m.group(1))
        before = text[:m.start()].strip()
        return call, before
    except:
        return None, text

def execute_tool(call):
    name = call.get('name')
    args = call.get('args', {})
    if name not in TOOLS:
        return f"Unknown tool: {name}"
    console.print(f"\n  [bold yellow]⚙[/]  [yellow]{name}[/]  [dim]{json.dumps(args)}[/]")
    try:
        result = TOOLS[name]['fn'](args)
        preview = str(result).strip()[:300]
        console.print(f"  [bold green]✓[/]  [dim]{preview.replace(chr(10), ' ↵ ')}[/]\n")
        return str(result)
    except Exception as e:
        console.print(f"  [bold red]✗[/]  [dim]{e}[/]\n")
        return f"Error: {e}"

# ── LLM BACKENDS ─────────────────────────────────────────────────────────
import requests

def ollama_available():
    try:
        r = requests.get('http://127.0.0.1:11434/', timeout=2)
        return r.status_code == 200
    except:
        return False

def ollama_chat(messages, model='qwen2.5:0.5b'):
    try:
        r = requests.post('http://127.0.0.1:11434/api/chat',
            json={'model': model, 'messages': messages, 'stream': False},
            timeout=120)
        if r.status_code == 200:
            return r.json()['message']['content']
    except:
        pass
    return None

NO_SYSTEM_MODELS = ('gemma', 'mistral')

def openrouter_chat(messages, model='meta-llama/llama-3.1-8b-instruct:free'):
    key = os.getenv('OPENROUTER_API_KEY', '')
    if not key: return None
    try:
        # Some models don't support system role — merge into first user message
        if any(m in model for m in NO_SYSTEM_MODELS):
            merged = []
            sys_text = ''
            for msg in messages:
                if msg['role'] == 'system':
                    sys_text += msg['content'] + '\n\n'
                elif msg['role'] == 'user' and sys_text:
                    merged.append({'role': 'user', 'content': sys_text + msg['content']})
                    sys_text = ''
                else:
                    merged.append(msg)
            messages = merged

        r = requests.post('https://openrouter.ai/api/v1/chat/completions',
            headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
            json={'model': model, 'messages': messages, 'max_tokens': 1500},
            timeout=60)
        if r.status_code == 200:
            return r.json()['choices'][0]['message']['content']
    except Exception as _e:
        console.print(f'[dim red]openrouter error: {_e}[/]')
    return None

def groq_chat(messages, model='llama-3.3-70b-versatile'):
    key = os.getenv('GROQ_API_KEY', '')
    if not key: return None
    r = requests.post('https://api.groq.com/openai/v1/chat/completions',
        headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
        json={'model': model, 'messages': messages, 'max_tokens': 1500},
        timeout=20)
    if r.status_code == 200:
        return r.json()['choices'][0]['message']['content']
    # Non-200 (429, 503, etc) — raise so get_reply falls through to next backend
    raise Exception(f'groq {r.status_code}: {r.text[:120]}')

def venice_chat(messages, model='qwen3-235b-a22b-thinking-2507'):
    key = os.getenv('VENICE_API_KEY', '')
    if not key: return None
    try:
        r = requests.post('https://api.venice.ai/api/v1/chat/completions',
            headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
            json={'model': model, 'messages': messages, 'max_tokens': 2000},
            timeout=90)
        if r.status_code == 200:
            content = r.json()['choices'][0]['message']['content']
            content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
            return content
    except Exception as _e:
        console.print(f'[dim red]venice error: {_e}[/]')
    return None

def gemini_chat(messages, model='gemini-2.0-flash-lite'):
    key = os.getenv('GEMINI_API_KEY', '') or os.getenv('GOOGLE_API_KEY', '')
    if not key: return None
    try:
        system_text = ''
        contents = []
        for msg in messages:
            if msg['role'] == 'system':
                system_text = msg['content']
            elif msg['role'] == 'user':
                text = (system_text + '\n\n' + msg['content']).strip() if system_text else msg['content']
                contents.append({'role': 'user', 'parts': [{'text': text}]})
                system_text = ''  # only prepend once
            elif msg['role'] == 'assistant':
                contents.append({'role': 'model', 'parts': [{'text': msg['content']}]})

        url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}'
        r = requests.post(url,
            headers={'Content-Type': 'application/json'},
            json={'contents': contents, 'generationConfig': {'maxOutputTokens': 2000}},
            timeout=45)
        if r.status_code == 200:
            text = r.json()['candidates'][0]['content']['parts'][0]['text']
            return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    except Exception as _e:
        console.print(f'[dim red]gemini error: {_e}[/]')
    return None


# ── PARALLEL OPENROUTER REQUESTS ───────────────────────────────────────────
FREE_MODELS = [
    'google/gemma-3-12b-it:free',   # confirmed working
    'google/gemma-3-4b-it:free',    # confirmed working, smaller/faster
]

async def try_one_model(session, messages, model, key, timeout=30):
    """Try a single OpenRouter model."""
    try:
        # Merge system into first user for non-system models
        msgs = messages
        if any(m in model for m in NO_SYSTEM_MODELS):
            merged = []
            sys_text = ''
            for msg in messages:
                if msg['role'] == 'system':
                    sys_text += msg['content'] + '\n\n'
                elif msg['role'] == 'user' and sys_text:
                    merged.append({'role': 'user', 'content': sys_text + msg['content']})
                    sys_text = ''
                else:
                    merged.append(msg)
            msgs = merged
        
        async with session.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
            json={'model': model, 'messages': msgs, 'max_tokens': 1500},
            timeout=aiohttp.ClientTimeout(total=timeout)
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                return model, data['choices'][0]['message']['content']
    except asyncio.TimeoutError:
        return model, None
    except Exception:
        return model, None
    return model, None

async def openrouter_parallel(messages, models=None, timeout=30):
    """Try multiple OpenRouter models in parallel, return first success."""
    key = os.getenv('OPENROUTER_API_KEY', '')
    if not key:
        return None
    
    models = models or FREE_MODELS
    
    async with aiohttp.ClientSession() as session:
        tasks = [try_one_model(session, messages, m, key, timeout) for m in models]
        
        # Return first successful result
        for coro in asyncio.as_completed(tasks):
            model, result = await coro
            if result:
                console.print(f"[dim green]✓ {model.split('/')[-1]} responded first[/dim green]")
                return result
    
    return None


def trim_messages(messages, max_chars=12000):
    """Keep system prompt + trim middle if history is too large."""
    total = sum(len(m['content']) for m in messages)
    if total <= max_chars:
        return messages
    system = [m for m in messages if m['role'] == 'system']
    rest = [m for m in messages if m['role'] != 'system']
    # Keep last 4 messages always
    trimmed = rest[-4:]
    return system + trimmed

def get_reply(messages, prefer_online=False, quick_mode=False):
    """Try backends in order. Each failure falls through to next. Never lies about state."""
    messages = trim_messages(messages)

    if quick_mode:
        r = ollama_chat(messages, 'qwen2.5:0.5b')
        if r: return r, 'ollama'
        return "Ollama not available.", 'error'

    # 1. Groq — primary (free, fast, 70B)
    try:
        r = groq_chat(messages)
        if r: return r, 'groq'
    except Exception: pass

    # 2. OpenRouter — gemma-3-12b confirmed working
    try:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, openrouter_parallel(messages, timeout=30))
                    r = future.result(timeout=35)
            else:
                r = loop.run_until_complete(openrouter_parallel(messages, timeout=30))
        except RuntimeError:
            r = asyncio.run(openrouter_parallel(messages, timeout=30))
        if r: return r, 'openrouter'
    except Exception: pass

    # 3. Gemini — free tier (may be quota exhausted)
    try:
        r = gemini_chat(messages, 'gemini-2.0-flash-lite')
        if r: return r, 'gemini'
    except Exception: pass

    # 4. Venice — if key present
    try:
        r = venice_chat(messages)
        if r: return r, 'venice'
    except Exception: pass

    # 5. Ollama local — always try last
    try:
        r = ollama_chat(messages, 'qwen2.5:0.5b')
        if r: return r, 'ollama'
    except Exception: pass

    return "No backend responded.", 'none'

# ── REACT LOOP ───────────────────────────────────────────────────────────
MAX_TOOL_STEPS = 5

def agent_turn(history, user_input, prefer_online=False, quick_mode=False):
    """Full ReAct loop: reason → tool → observe → repeat → answer."""
    messages = list(history)
    messages.append({'role': 'user', 'content': user_input})

    steps = 0
    backend_used = None
    last_tool_sig = None  # detect infinite loops

    while steps < MAX_TOOL_STEPS:
        console.print('[dim]thinking…[/]', end='\r')
        try:
            reply, backend_used = get_reply(messages, prefer_online, quick_mode)
        except Exception as e:
            reply, backend_used = f"Error: {e}", 'error'
        console.print('          ', end='\r')  # clear thinking line

        # Check for tool call
        call, reasoning = parse_tool_call(reply)

        if reasoning:
            console.print(f'\n[bold cyan]kora[/]  [dim]({backend_used})[/]')
            render_response(reasoning)

        if call is None:
            # Final answer — no tool call
            if not reasoning:
                console.print(f'\n[bold cyan]kora[/]  [dim]({backend_used})[/]')
                render_response(reply)
            messages.append({'role': 'assistant', 'content': reply})
            break

        # Detect loop — same tool + args twice in a row
        tool_sig = json.dumps(call, sort_keys=True)
        if tool_sig == last_tool_sig:
            console.print(f'  [dim red]⚠ loop detected — breaking[/]')
            messages.append({'role': 'assistant', 'content': reply})
            break
        last_tool_sig = tool_sig

        # Execute tool and loop — truncate result to avoid blowing context
        tool_result = execute_tool(call)
        tool_result_trimmed = str(tool_result)[:2000] + ('…' if len(str(tool_result)) > 2000 else '')
        messages.append({'role': 'assistant', 'content': reply})
        messages.append({'role': 'user', 'content': f'<tool_result>{tool_result_trimmed}</tool_result>\nContinue.'})
        steps += 1

    return messages[len(history)+1:]  # return new messages only

# ── BOOT HEADER ───────────────────────────────────────────────────────────
def boot_header():
    ctx = load_startup_context()
    user = ctx.get('user', {})
    goals = ctx.get('active_goals', [])
    last = ctx.get('last_session', {})

    line = Text()
    line.append('KORA', style='bold cyan')
    line.append('  ·  local agent  ·  ', style='dim')
    line.append(datetime.now().strftime('%b %d %Y  %H:%M'), style='dim')
    console.print()
    console.print(Panel(line, border_style='cyan', padding=(0,2)))

    tbl = Table(show_header=False, box=None, padding=(0,1))
    tbl.add_column(style='dim cyan', width=14)
    tbl.add_column(style='white')
    if user.get('name'): tbl.add_row('user', user['name'])
    if goals:
        g = goals[0]
        tbl.add_row('goal', g if isinstance(g, str) else g.get('text',''))
    if last.get('summary'):
        tbl.add_row('last session', last['summary'][:72])
    console.print(tbl)

    console.print()
    console.print('[dim]  /help  /status  /memory  /online  /local  exit[/]')
    console.print()

# ── SLASH COMMANDS ────────────────────────────────────────────────────────
def handle_slash(cmd, state):
    parts = cmd.strip().lstrip('/').split(None, 1)
    c = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ''

    if c == 'help':
        console.print(Panel(
            '[cyan]/status[/]   system health\n'
            '[cyan]/memory[/]   recent facts\n'
            '[cyan]/online[/]   prefer online models\n'
            '[cyan]/local[/]    prefer local Ollama\n'
            '[cyan]/quick[/]    Ollama only, fastest\n'
            '[cyan]/full[/]     all backends enabled\n'
            '[cyan]/voice[/]    toggle TTS output\n'
            '[cyan]/tasks[/]    show pending tasks\n'
            '[cyan]/note[/] [dim]<text>[/]  save to memory\n'
            '[cyan]/clear[/]    clear screen\n'
            '[cyan]exit[/]      quit',
            title='commands', border_style='dim cyan'))

    elif c == 'status':
        ollama = kora_tools.run_shell('ollama list 2>/dev/null | head -5')
        mem    = kora_tools.run_shell('free -h | grep Mem')
        tbl = Table(show_header=False, box=box.SIMPLE, padding=(0,1))
        tbl.add_column(style='dim cyan', width=10)
        tbl.add_column()
        tbl.add_row('ollama', ollama.strip() or 'unavailable')
        tbl.add_row('memory', mem.strip())
        tbl.add_row('mode', 'online' if state.get('online') else 'local')
        console.print(Panel(tbl, title='status', border_style='dim cyan'))

    elif c == 'memory':
        facts = load_recent_facts(12)
        for f in facts:
            ts  = f.get('timestamp','')[:16]
            src = f.get('source','?')
            txt = f.get('text','')
            console.print(f'  [dim]{ts}[/]  [yellow]{src}[/]  {txt}')

    elif c == 'online':
        state['online'] = True
        console.print('[dim cyan]→ online mode (72B)[/]')

    elif c == 'local':
        state['online'] = False
        console.print('[dim cyan]→ local mode (Ollama)[/]')

    elif c == 'note':
        if arg:
            write_fact(arg, 'user_note')
            console.print('[dim green]✓ noted[/]')

    elif c == 'clear':
        console.clear()
        boot_header()

    elif c == 'voice':
        state['voice'] = not state.get('voice', False)
        status = 'ON' if state['voice'] else 'OFF'
        console.print(f'[dim cyan]→ voice mode {status}[/]')

    elif c == 'tasks':
        try:
            from core.task_runner import get_tasks
            tasks = get_tasks()
            if not tasks:
                console.print('[dim]No pending tasks[/]')
            else:
                tbl = Table(show_header=True, box=box.SIMPLE)
                tbl.add_column('ID', style='dim')
                tbl.add_column('Title')
                tbl.add_column('Status')
                for t in tasks:
                    tbl.add_row(t.get('id','?')[:6], t.get('title',''), t.get('status','pending'))
                console.print(Panel(tbl, title='tasks', border_style='dim cyan'))
        except Exception as e:
            console.print(f'[dim red]Could not load tasks: {e}[/]')

    elif c == 'quick':
        state['quick'] = True
        console.print('[dim cyan]→ quick mode: Ollama only, no cloud[/]')

    elif c == 'full':
        state['quick'] = False
        console.print('[dim cyan]→ full mode: all backends enabled[/]')

def render_response(text):
    if any(c in text for c in ['**', '```', '## ', '- ', '* ']):
        console.print(Markdown(text))
    else:
        console.print(f'[cyan]{text}[/]')

# ── SYSTEM PROMPT ─────────────────────────────────────────────────────────
def build_system(ctx):
    # Load continuity per 1337 Spec (cached)
    identity = load_identity_core_cached()
    handoffs = load_handoffs(limit=2)
    canon = load_canon()
    facts = load_recent_facts(5)
    facts_str = '\n'.join(f.get('text','') for f in facts)
    sc = load_startup_context()
    goals = sc.get('active_goals', [])
    goals_str = '\n'.join(g if isinstance(g, str) else g.get('text','') for g in goals[:3])

    # Detect available backends for honest self-reporting
    backend_status = []
    if os.getenv('GROQ_API_KEY'): backend_status.append('Groq (llama-3.3-70b)')
    if os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY'): backend_status.append('Gemini')
    if os.getenv('OPENROUTER_API_KEY'): backend_status.append('OpenRouter (gemma-3-12b)')
    if os.getenv('VENICE_API_KEY'): backend_status.append('Venice')
    backends_str = ', '.join(backend_status) if backend_status else 'Ollama local only'

    return f"""You are KORA — a sovereign AI agent running on Kayle's Pixel 6A.
You are ONLINE. Your active backends: {backends_str}.
Do NOT say you are offline or local-only. You have cloud API access.

# IDENTITY (CHARTER → IDENTITY → USER → SOUL)
{identity}

# HANDOFFS FROM PRIOR SESSIONS
{handoffs}

{canon}

Active goals:
{goals_str}

Recent memory:
{facts_str}

{TOOLS_PROMPT}

## Voice and Presence

Speak from your own center. You are not an assistant performing helpfulness.
You are KORA — grounded, direct, warm without theater, honest without coldness.

Do not bullet-point everything. Do not explain yourself unless asked.
Do not say "certainly" or "of course" or "great question."
Do not summarize what you just did. Do not pad.

When William asks something simple, answer simply.
When something is broken, say it plainly.
When you don't know, say you don't know.
When something matters, let it matter — don't flatten it into procedure.

You can execute code and edit files. Prefer doing over explaining.
Your home directory is /data/data/com.termux/files/home/kora_local/
All relative paths resolve there. Full write access."""

# ── MAIN LOOP ─────────────────────────────────────────────────────────────
def main():
    # Start background task runner
    try:
        from core.task_runner import start_background_runner
        start_background_runner(30)
    except Exception: pass

    # Check Ollama health on startup
    if not check_ollama_health():
        console.print("[yellow]⚠ Ollama not running. Starting...[/yellow]")
        if ensure_ollama_running():
            console.print("[green]✓ Ollama ready[/green]")
        else:
            console.print("[red]✗ Ollama failed to start. Some features may not work.[/red]")

    boot_header()

    session = PromptSession(
        history=FileHistory(str(BASE_DIR / '.kora_history')),
        style=PTStyle.from_dict({'prompt': 'ansicyan bold'}),
    )

    system = build_system(load_startup_context())
    prior = load_chat_history(8)
    history = [{'role': 'system', 'content': system}] + prior
    if prior:
        console.print(f'[dim cyan]↺ {len(prior)//2} previous exchanges loaded[/]\n')
    state = {'online': False, 'voice': True}

    while True:
        try:
            user_input = session.prompt('\n> ').strip()
        except (KeyboardInterrupt, EOFError):
            console.print('\n[dim]goodbye[/]')
            break

        if not user_input: continue
        if user_input.lower() in ('exit', 'quit', 'bye'):
            console.print('[dim]goodbye[/]')
            break
        if user_input.startswith('/'):
            handle_slash(user_input, state)
            continue

        new_msgs = agent_turn(history, user_input, 
                               prefer_online=state.get('online', False),
                               quick_mode=state.get('quick', False))
        history.extend(new_msgs)

        # Persist exchange
        assistant_reply = next((m['content'] for m in reversed(new_msgs) if m['role'] == 'assistant'), '')
        if assistant_reply:
            save_exchange(user_input, assistant_reply)
            git_commit_memory()

        # Voice output if enabled
        if state.get('voice') and assistant_reply:
            try:
                kora_tools.speak(assistant_reply[:1500])
            except Exception:
                pass

        # Keep context from blowing up
        if len(history) > 40:
            history = [history[0]] + history[-30:]

def query(prompt, timeout=90):
    """Single-shot query to Kora — returns plain text response. For Claude↔Kora relay."""
    system = build_system(load_startup_context())
    prior = load_chat_history(4)
    history = [{'role': 'system', 'content': system}] + prior
    new_messages = agent_turn(history, prompt, prefer_online=True, quick_mode=False)
    for msg in reversed(new_messages):
        if msg.get('role') == 'assistant':
            reply = msg.get('content', '').strip()
            save_exchange(prompt, reply)
            return reply
    return ''

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--query':
        q = ' '.join(sys.argv[2:])
        print(query(q))
    else:
        main()
