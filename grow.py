"""
Kora's growth engine.

Kora grows by addition: new skills are proposed, tested, and promoted
into a separate growth directory. kora.py is never touched by this system.

Directory layout:
  growth/
    manifest.json          registry of all promoted skills
    proposals/
      <name>.py            generated code
      <name>.meta.json     proposal metadata and test results
    skills/
      <name>.py            promoted, loadable code
"""

import os
import json
import datetime
import subprocess
import sys
import importlib.util

GROWTH_DIR    = os.path.expanduser("~/kora/growth")
SKILLS_DIR    = os.path.join(GROWTH_DIR, "skills")
PROPOSALS_DIR = os.path.join(GROWTH_DIR, "proposals")
MANIFEST      = os.path.join(GROWTH_DIR, "manifest.json")
LEDGER_FILE   = os.path.expanduser("~/kora/ledger.jsonl")


def _ensure_dirs():
    for d in [SKILLS_DIR, PROPOSALS_DIR]:
        os.makedirs(d, exist_ok=True)


# --- MANIFEST ---

def load_manifest():
    if os.path.exists(MANIFEST):
        with open(MANIFEST) as f:
            return json.load(f)
    return {}


def save_manifest(m):
    with open(MANIFEST, "w") as f:
        json.dump(m, f, indent=2)


# --- PROPOSAL METADATA ---

def _meta_path(name):
    return os.path.join(PROPOSALS_DIR, f"{name}.meta.json")


def _code_path(name):
    return os.path.join(PROPOSALS_DIR, f"{name}.py")


def load_meta(name):
    path = _meta_path(name)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def save_meta(meta):
    with open(_meta_path(meta["name"]), "w") as f:
        json.dump(meta, f, indent=2)


# --- LEDGER ---

def _log_event(event):
    with open(LEDGER_FILE, "a") as f:
        f.write(json.dumps({"ts": datetime.datetime.now().isoformat(), "growth": event}) + "\n")


# --- PROPOSE ---

def propose(name, description, ask_ollama_fn, model_name="unknown"):
    """
    Ask Ollama to write a skill module. Save code and metadata to proposals/.
    Returns (code_path, code_str).
    """
    _ensure_dirs()

    prompt = (
        f"Write a single Python function called `{name}` that does the following:\n"
        f"{description}\n\n"
        "Rules:\n"
        "- Plain Python only. Imports allowed: stdlib and `requests`.\n"
        "- The function must be self-contained.\n"
        "- Include a one-line docstring inside the function.\n"
        "- Optionally, add a `selftest()` function below it that calls `{name}()` "
        "with safe test inputs and raises AssertionError on failure.\n"
        "- Return only raw Python code. No markdown. No explanation."
    ).format(name=name)

    code = ask_ollama_fn(prompt).strip()

    # Strip markdown fences if model wrapped them anyway
    if code.startswith("```"):
        lines = code.splitlines()
        code = "\n".join(l for l in lines if not l.startswith("```")).strip()

    code_path = _code_path(name)
    with open(code_path, "w") as f:
        f.write(code)

    meta = {
        "name": name,
        "description": description,
        "created_at": datetime.datetime.now().isoformat(),
        "generated_by_model": model_name,
        "test_status": "pending",
        "test_output": None,
        "test_run_at": None,
        "promoted_at": None,
    }
    save_meta(meta)
    _log_event({"action": "propose", "name": name, "description": description})

    return code_path, code


# --- TEST ---

def test_proposal(name):
    """
    Test a proposal. Three steps, in order:
      1. Syntax check (compile)
      2. Import-level execution check (not a sandbox — runs in a child process
         with full filesystem access; it only isolates the process, not the environment)
      3. selftest() if the module defines one

    Updates proposal metadata with result.
    Returns (passed: bool, output: str).
    """
    code_path = _code_path(name)
    meta = load_meta(name)
    if not meta:
        return False, "Proposal metadata not found."
    if not os.path.exists(code_path):
        return False, "Proposal code file not found."

    with open(code_path) as f:
        source = f.read()

    # Step 1: syntax check
    try:
        compile(source, code_path, "exec")
    except SyntaxError as e:
        return _record_test(meta, passed=False, output=f"SyntaxError: {e}")

    # Step 2: import-level execution check (child process, not a true sandbox)
    check_script = (
        f"import importlib.util, sys\n"
        f"spec = importlib.util.spec_from_file_location('{name}', '{code_path}')\n"
        f"mod = importlib.util.module_from_spec(spec)\n"
        f"spec.loader.exec_module(mod)\n"
        f"print('import_ok')\n"
        f"if hasattr(mod, 'selftest') and callable(mod.selftest):\n"
        f"    mod.selftest()\n"
        f"    print('selftest_ok')\n"
    )
    try:
        proc = subprocess.run(
            [sys.executable, "-c", check_script],
            capture_output=True, text=True, timeout=15
        )
    except subprocess.TimeoutExpired:
        return _record_test(meta, passed=False, output="Timed out after 15 seconds.")

    combined = (proc.stdout + proc.stderr).strip()
    passed = proc.returncode == 0 and "import_ok" in proc.stdout

    return _record_test(meta, passed=passed, output=combined)


def _record_test(meta, passed, output):
    meta["test_status"]  = "passed" if passed else "failed"
    meta["test_output"]  = output
    meta["test_run_at"]  = datetime.datetime.now().isoformat()
    save_meta(meta)
    _log_event({"action": "test", "name": meta["name"], "passed": passed, "output": output})
    return passed, output


# --- PROMOTE ---

def promote(name):
    """
    Promote a proposal to skills/. Requires test_status == 'passed'.
    Registers entry in manifest. Returns (success: bool, message: str).
    """
    meta = load_meta(name)
    if not meta:
        return False, "Proposal metadata not found."

    if meta.get("test_status") != "passed":
        status = meta.get("test_status", "pending")
        return False, f"Cannot promote: test status is '{status}', must be 'passed'."

    src = _code_path(name)
    dst = os.path.join(SKILLS_DIR, f"{name}.py")

    with open(src) as f:
        code = f.read()
    with open(dst, "w") as f:
        f.write(code)

    now = datetime.datetime.now().isoformat()
    meta["promoted_at"] = now
    save_meta(meta)

    manifest = load_manifest()
    manifest[name] = {
        "file": dst,
        "description": meta["description"],
        "generated_by_model": meta["generated_by_model"],
        "promoted_at": now,
    }
    save_manifest(manifest)
    _log_event({"action": "promote", "name": name})

    return True, dst


# --- LOAD ---

def load_skills():
    """
    Import all promoted skills from manifest.
    Returns dict of name -> callable (the function matching the skill name).
    Silently skips entries that fail to import.
    """
    manifest = load_manifest()
    skills = {}
    for name, entry in manifest.items():
        path = entry.get("file")
        if not path or not os.path.exists(path):
            continue
        try:
            spec = importlib.util.spec_from_file_location(name, path)
            mod  = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            fn = getattr(mod, name, None)
            if callable(fn):
                skills[name] = fn
        except Exception:
            pass
    return skills


# --- STATUS ---

def list_proposals():
    """Return metadata for all proposals, sorted by created_at."""
    results = []
    for fname in os.listdir(PROPOSALS_DIR) if os.path.exists(PROPOSALS_DIR) else []:
        if fname.endswith(".meta.json"):
            with open(os.path.join(PROPOSALS_DIR, fname)) as f:
                results.append(json.load(f))
    return sorted(results, key=lambda m: m.get("created_at", ""))
