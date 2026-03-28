import subprocess

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
