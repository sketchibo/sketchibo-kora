from pathlib import Path

p = Path.home() / "kora_local" / "kora.py"
txt = p.read_text()

def replace_block(txt, start_marker, end_marker, new_block):
    start = txt.find(start_marker)
    end = txt.find(end_marker, start)
    return txt[:start] + new_block + txt[end:]

# --- NEW run_fast ---
run_fast_new = '''
def run_fast(user_prompt: str, model_override: str = None) -> str:
    empathy_block = empathy_context_block(user_prompt, mode="fast")
    startup_brief = startup_context_brief(STARTUP_CONTEXT)

    parts = []
    if startup_brief:
        parts.append(startup_brief)
    if empathy_block:
        parts.append(empathy_block)
    parts.append("## User Request\\n" + user_prompt)

    full_prompt = "\\n\\n".join(parts)

    # 1. Gemini
    out = gemini_generate(full_prompt, timeout=45)
    if out and not out.startswith("GEMINI_"):
        return out

    # 2. OpenRouter free
    for model in FREE_OPENROUTER_MODELS:
        out = openrouter_chat(full_prompt, timeout=45, model_override=model)
        if out:
            return out

    # 3. Venice
    out = venice_chat(full_prompt, timeout=45)
    if out:
        return out

    # 4. Local fallback
    return ollama_generate(FAST_LOCAL_MODELS[0], full_prompt, timeout=60)
'''

# --- NEW run_council ---
run_council_new = '''
def run_council(user_prompt: str) -> str:
    facts = facts_preview(limit=5)
    state = self_reflect()
    context = load_canon_files().strip()

    council_prompt = f"""
You are KORA.

PROFILE CONTEXT:
{context}

STATE:
{state}

FACTS:
{facts}

USER:
{user_prompt}

Respond with:
Healthy
Fragile
Missing
Next Move
"""

    # 1. Gemini
    out = gemini_generate(council_prompt, timeout=60)
    if out and not out.startswith("GEMINI_"):
        return out

    # 2. OpenRouter
    for model in FREE_OPENROUTER_MODELS:
        out = openrouter_chat(council_prompt, timeout=60, model_override=model)
        if out:
            return out

    # 3. Venice
    out = venice_chat(council_prompt, timeout=60)
    if out:
        return out

    # 4. Local fallback
    return ollama_generate(FAST_LOCAL_MODELS[0], council_prompt, timeout=60)
'''

# Replace blocks
txt = replace_block(txt, "def run_fast", "def run_council", run_fast_new)
txt = replace_block(txt, "def run_council", "def handle_cli", run_council_new)

p.write_text(txt)
print("FUNCTIONS_FIXED")
