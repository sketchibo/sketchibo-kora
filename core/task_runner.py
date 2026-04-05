#!/usr/bin/env python3
"""
core/task_runner.py — KORA autonomous task queue
Tasks persist in memory/task_queue.json and execute in background.
"""

import json, os, subprocess, threading, time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
QUEUE_FILE = BASE_DIR / 'memory' / 'task_queue.json'

def load_queue():
    if not QUEUE_FILE.exists(): return []
    try: return json.loads(QUEUE_FILE.read_text())
    except: return []

def save_queue(tasks):
    QUEUE_FILE.write_text(json.dumps(tasks, indent=2))

def add_task(title, command=None, note=None, trigger='now'):
    tasks = load_queue()
    task = {
        'id': int(time.time()),
        'title': title,
        'command': command,
        'note': note,
        'trigger': trigger,
        'status': 'pending',
        'created': datetime.now().isoformat(),
        'result': None
    }
    tasks.append(task)
    save_queue(tasks)
    return task['id']

def complete_task(task_id, result):
    tasks = load_queue()
    for t in tasks:
        if t['id'] == task_id:
            t['status'] = 'done'
            t['result'] = str(result)[:500]
            t['completed'] = datetime.now().isoformat()
    save_queue(tasks)

def fail_task(task_id, error):
    tasks = load_queue()
    for t in tasks:
        if t['id'] == task_id:
            t['status'] = 'failed'
            t['result'] = str(error)[:300]
    save_queue(tasks)

def list_tasks(status=None):
    tasks = load_queue()
    if status:
        tasks = [t for t in tasks if t['status'] == status]
    return tasks

def run_pending():
    """Execute all pending 'now' tasks. Call from background thread."""
    tasks = load_queue()
    for t in tasks:
        if t['status'] != 'pending': continue
        if t['trigger'] != 'now': continue
        if not t.get('command'): continue
        try:
            result = subprocess.run(t['command'], shell=True,
                capture_output=True, text=True, timeout=60)
            out = result.stdout.strip() or result.stderr.strip() or '(done)'
            complete_task(t['id'], out)
        except Exception as e:
            fail_task(t['id'], str(e))

def start_background_runner(interval=30):
    """Run pending tasks every N seconds in background thread."""
    def loop():
        while True:
            try: run_pending()
            except: pass
            time.sleep(interval)
    t = threading.Thread(target=loop, daemon=True)
    t.start()
    return t

def status_summary():
    tasks = load_queue()
    pending = [t for t in tasks if t['status'] == 'pending']
    done    = [t for t in tasks if t['status'] == 'done']
    failed  = [t for t in tasks if t['status'] == 'failed']
    lines = [f"Tasks: {len(pending)} pending  {len(done)} done  {len(failed)} failed"]
    for t in pending[:5]:
        lines.append(f"  ⏳ [{t['id']}] {t['title']}")
    for t in failed[-3:]:
        lines.append(f"  ✗ [{t['id']}] {t['title']}: {t.get('result','')[:60]}")
    return '\n'.join(lines)
