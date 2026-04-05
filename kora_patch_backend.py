import re
from pathlib import Path

p = Path.home() / "kora_local" / "kora.py"
txt = p.read_text()

# --- Replace model definitions ---
txt = re.sub(
    r'FAST_LOCAL_MODELS\s*=\s*\[.*?\]\s*\nCOUNCIL_LOCAL_MODELS\s*=\s*\[.*?\]',
    '''FAST_LOCAL_MODELS = ["qwen2.5:7b"]  # local fallback only

FREE_OPENROUTER_MODELS = [
    "meta-llama/llama-3.1-8b-instruct:free",
    "mistralai/mistral-7b-instruct:free",
    "qwen/qwen-2.5-7b-instruct:free",
]

COUNCIL_MODELS = ["gemini", "openrouter", "venice"]''',
    txt,
    flags=re.DOTALL
)

# --- Patch run_fast ---
txt = re.sub(
    r'out = gemini_generate\(full_prompt, timeout=45\).*?return ollama_generate\(FAST_LOCAL_MODELS\[0\], full_prompt, timeout=60\)',
    '''# 1. Gemini (free, fast)
out = gemini_generate(full_prompt, timeout=45)
if out and not out.startswith("GEMINI_"):
    return out

# 2. OpenRouter free rotation
for model in FREE_OPENROUTER_MODELS:
    out = openrouter_chat(full_prompt, timeout=45, model_override=model)
    if out:
        return out

# 3. Venice (paid fallback)
out = venice_chat(full_prompt, timeout=45)
if out:
    return out

# 4. Local fallback
return ollama_generate(FAST_LOCAL_MODELS[0], full_prompt, timeout=60)''',
    txt,
    flags=re.DOTALL
)

# --- Patch run_council ---
txt = re.sub(
    r'return ollama_generate\("tinyllama", council_prompt, timeout=60\)',
    '''# 1. Gemini
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
return ollama_generate(FAST_LOCAL_MODELS[0], council_prompt, timeout=60)''',
    txt
)

p.write_text(txt)
print("PATCH_APPLIED")
