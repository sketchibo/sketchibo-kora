#!/usr/bin/env python3
import re
import shutil
from datetime import datetime
from pathlib import Path

path = Path.home() / 'kora' / 'kora.py'
text = path.read_text(encoding='utf-8')

bak = path.with_name(f'kora.py.bak_pre_confinement_{datetime.now():%Y%m%d_%H%M%S}')
shutil.copy2(path, bak)

import_block = '''
try:
    from kora_confinement import get_tier, log_confinement_event
except Exception:
    def get_tier():
        return 0

    def log_confinement_event(*args, **kwargs):
        return None
'''.strip() + '\n\n'

if 'from kora_confinement import get_tier, log_confinement_event' not in text:
    if 'import kora_tools\n' not in text:
        raise SystemExit('PATCH_FAIL: could not find import kora_tools line')
    text = text.replace('import kora_tools\n', 'import kora_tools\n' + import_block, 1)

helper_block = '''
ACTION_TIER_REQUIREMENTS = {
    'get_system_status': 0,
    'list_files': 0,
    'read_file': 0,
    'view_memory': 0,
    'remember_append': 1,
    'run_shell': 3,
    'write_file': 4,
    'patch_file': 4,
}

def _kscp_log(message: str) -> None:
    try:
        log_confinement_event(message)
        return
    except TypeError:
        try:
            log_confinement_event('kora.py', message)
            return
        except Exception:
            return
    except Exception:
        return

def confinement_check(intent_name: str, args=None):
    required = ACTION_TIER_REQUIREMENTS.get(intent_name, 4)
    try:
        current = int(get_tier())
    except Exception:
        current = 0

    if current < required:
        msg = f'K-SCP: blocked {intent_name} (tier {current} < required {required})'
        _kscp_log(msg)
        return False, msg

    return True, ''

def guarded_remember(kind: str, text: str) -> str:
    ok, deny = confinement_check('remember_append', {'kind': kind, 'text': text})
    if not ok:
        return deny
    return remember(kind, text)
'''.strip() + '\n\n'

if 'def confinement_check(' not in text:
    if '\ndef main():\n' not in text:
        raise SystemExit('PATCH_FAIL: could not find def main()')
    text = text.replace('\ndef main():\n', '\n' + helper_block + 'def main():\n', 1)

text = text.replace(
    'remember(kind.strip(), text.strip())',
    'guarded_remember(kind.strip(), text.strip())'
)
text = text.replace(
    'remember("journal", text)',
    'guarded_remember("journal", text)'
)

approve_old = '''        if ul == "approve":
            if pending_action:
                if pending_action["intent"] == "patch_file":
                    args = pending_action["args"]
                    print("\\nKORA:", kora_tools.patch_file(args["path"], args["instruction"]))
                    pending_action = None
                    continue
'''

approve_new = '''        if ul == "approve":
            if pending_action:
                if pending_action["intent"] == "patch_file":
                    args = pending_action["args"]
                    ok, deny = confinement_check("patch_file", args)
                    if not ok:
                        print(f"\\nKORA: {deny}")
                        pending_action = None
                        continue
                    print("\\nKORA:", kora_tools.patch_file(args["path"], args["instruction"]))
                    pending_action = None
                    continue
'''

if 'confinement_check("patch_file", args)' not in text:
    if approve_old not in text:
        raise SystemExit('PATCH_FAIL: could not patch approve block')
    text = text.replace(approve_old, approve_new, 1)

action_pattern = re.compile(
    r'(?P<indent>\s*)intent = interpret\(u\)\n'
    r'(?P=indent)if intent\["mode"\] == "action"(?: and intent\.get\("confidence", 0\) >= 0\.85)?:\n'
    r'(?P=indent)    i = intent\["intent"\]\n'
    r'(?P=indent)    args = intent\["args"\]\n'
)

def action_repl(m):
    ind = m.group('indent')
    return (
        f'{ind}intent = interpret(u)\n'
        f'{ind}if intent["mode"] == "action" and intent.get("confidence", 0) >= 0.85:\n'
        f'{ind}    i = intent["intent"]\n'
        f'{ind}    args = intent["args"]\n'
        f'{ind}    ok, deny = confinement_check(i, args)\n'
        f'{ind}    if not ok:\n'
        f'{ind}        print(f"\\nKORA: {{deny}}")\n'
        f'{ind}        continue\n'
    )

text, n = action_pattern.subn(action_repl, text, count=1)
if n != 1:
    raise SystemExit('PATCH_FAIL: could not patch action dispatch block')

path.write_text(text, encoding='utf-8')
print(f'PATCH_OK {path}')
print(f'BACKUP_OK {bak}')
