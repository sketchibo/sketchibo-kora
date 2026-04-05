import re
from pathlib import Path

p = Path.home() / "kora_local" / "kora.py"
txt = p.read_text()

# --- Inject memory into run_fast ---
txt = re.sub(
    r'(def run_fast\(.*?parts = \[\])',
    r'\1\n    memory_block = memory_view("facts")',
    txt,
    flags=re.DOTALL
)

txt = txt.replace(
    'parts.append("## User Request\\n" + user_prompt)',
    'parts.append("## Memory\\n" + memory_block)\n    parts.append("## User Request\\n" + user_prompt)'
)

# --- Inject memory into run_council ---
txt = re.sub(
    r'(def run_council\(.*?facts = facts_preview\(limit=5\))',
    r'\1\n    memory_block = memory_view("facts")',
    txt,
    flags=re.DOTALL
)

txt = txt.replace(
    '"PINNED FACTS:\\n"\n        f"{facts}\\n\\n"',
    '"PINNED FACTS:\\n"\n        f"{facts}\\n\\n"\n        "MEMORY:\\n"\n        f"{memory_block}\\n\\n"'
)

p.write_text(txt)
print("MEMORY_PATCH_APPLIED")
