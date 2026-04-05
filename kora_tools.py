"""
Compatibility facade for KORA tools.
Real implementations now live in tools/.
"""

from tools.adb_tools import adb, tv_screenshot
from tools.file_tools import run_shell, write_file, read_file
from tools.web_tools import web_search

# Optional modules (safe fallback if missing)

def speak(text):
    try:
        from tools.speech import speak as _s
        return _s(text)
    except:
        return "(tts unavailable)"

def queue_task(*a, **k):
    try:
        from tools.task_tools import queue_task as _q
        return _q(*a, **k)
    except:
        return "(task queue unavailable)"

def task_status():
    try:
        from tools.task_tools import task_status as _s
        return _s()
    except:
        return "(task queue unavailable)"
