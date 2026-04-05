from pathlib import Path

p = Path.home() / "kora_local" / "kora.py"
lines = p.read_text().splitlines()

new_lines = []
inside = False

for line in lines:
    if line.strip().startswith("def selfcheck"):
        inside = True
        new_lines.append("def selfcheck():")
        new_lines.append("    base = Path.home() / 'kora_local'")
        new_lines.append("    mem = base / 'memory'")
        new_lines.append("")
        new_lines.append("    def chk(name):")
        new_lines.append("        f = mem / name")
        new_lines.append("        if not f.exists(): return f'{name}: MISSING'")
        new_lines.append("        if f.stat().st_size == 0: return f'{name}: EMPTY'")
        new_lines.append("        return f'{name}: OK'")
        new_lines.append("")
        new_lines.append("    print('SELF MEMORY CHECK')")
        new_lines.append("    print(chk('facts.jsonl'))")
        new_lines.append("    print(chk('lce_profile.json'))")
        new_lines.append("    print(chk('person_model.json'))")
        new_lines.append("    print(chk('trajectory.json'))")
        continue

    if inside:
        if line.startswith("def ") and not line.strip().startswith("def selfcheck"):
            inside = False
            new_lines.append(line)
        # skip old selfcheck body
    else:
        new_lines.append(line)

p.write_text("\n".join(new_lines))
print("SELFCHECK_FIXED")
