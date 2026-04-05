from pathlib import Path
import json

p = Path.home() / "kora_local" / "kora.py"
txt = p.read_text()

def new_selfcheck():
    base = Path.home() / "kora_local"

    memory_dir = base / "memory"

    checks = []

    def check_file(name):
        f = memory_dir / name
        if not f.exists():
            return f"{name}: MISSING"
        if f.stat().st_size == 0:
            return f"{name}: EMPTY"
        return f"{name}: OK"

    checks.append(check_file("facts.jsonl"))
    checks.append(check_file("lce_profile.json"))
    checks.append(check_file("person_model.json"))
    checks.append(check_file("trajectory.json"))

    return "\\n".join(checks)

import re

txt = re.sub(
    r'def selfcheck\(.*?\n\)',
    '''def selfcheck():
    print("SELF MEMORY CHECK")
    print(new_selfcheck())
''',
    txt,
    flags=re.DOTALL
)

txt = "from pathlib import Path\\n\\n" + txt
txt = txt.replace("import json", "import json\\n" + new_selfcheck.__code__.co_consts[0])

p.write_text(txt)

print("SELFCHECK_PATCHED")
