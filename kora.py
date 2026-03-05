import os
import requests
import time

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

# --- Venice config ---
VENICE_API_KEY = os.getenv("VENICE_API_KEY", "").strip()
VENICE_URL = "https://api.venice.ai/api/v1/chat/completions"
VENICE_MODEL = "venice-uncensored"

LOCAL_MODELS = [
    "qwen2.5:7b",
    "llama3.1:8b",
    "dolphin-phi:latest"
]

def ollama_generate(model, prompt):
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }

    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=60)
        r.raise_for_status()
        return r.json().get("response", "")
    except Exception as e:
        return f"[ERROR {model}: {e}]"

def call_venice(prompt):
    if not VENICE_API_KEY:
        return "[VENICE ERROR: key not loaded]"

    headers = {
        "Authorization": f"Bearer {VENICE_API_KEY}",
        "x-api-key": VENICE_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "model": VENICE_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    try:
        r = requests.post(VENICE_URL, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[VENICE ERROR: {e}]"

def council(prompt):
    drafts = {}

    for model in LOCAL_MODELS:
        drafts[model] = ollama_generate(model, prompt)

    merged = "\n\n".join(drafts.values())

    final = call_venice(
        f"User question:\n{prompt}\n\nDraft answers:\n{merged}\n\nProduce the best final answer."
    )

    return final

def venice_chat(prompt):
    try:
        response = call_venice(prompt)
        if response:
            return response
    except Exception as e:
        print(f"[VENICE ERROR: {e}]")

    return ollama_generate("qwen2.5:7b", prompt)

def main():
    print("=== KORA COUNCIL ONLINE ===")

    while True:
        u = input("\nYou: ").strip()

        if u.lower() in ["exit", "quit"]:
            break

        result = council(u)
        print("\nKORA:", result)

if __name__ == "__main__":
    main()
