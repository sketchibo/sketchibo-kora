#!/usr/bin/env bash
set -euo pipefail

PROMPT="${*:-Say: KORA is online.}"

if [ -z "${GEMINI_API_KEY:-}" ]; then
  echo "GEMINI_API_KEY is not set"
  exit 1
fi

ask_ollama() {
  local model="$1"
  local prompt="$2"
  curl -s http://127.0.0.1:11434/api/generate \
    -d "$(jq -nc --arg model "$model" --arg prompt "$prompt" \
      '{model:$model,prompt:$prompt,stream:false}')" \
    | jq -r '.response'
}

QWEN_REPLY="$(ask_ollama 'qwen2.5:7b' "$PROMPT")"
DOLPHIN_REPLY="$(ask_ollama 'dolphin-phi:latest' "$PROMPT")"

MERGE_PROMPT=$(cat <<TXT
User prompt:
$PROMPT

Qwen reply:
$QWEN_REPLY

Dolphin reply:
$DOLPHIN_REPLY

Combine the strongest parts of both replies into one final answer.
Prefer clarity, coherence, and usefulness.
Do not mention the models.
TXT
)

curl -sS \
  -H "Content-Type: application/json" \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${GEMINI_API_KEY}" \
  -d "$(jq -nc --arg p "$MERGE_PROMPT" '{contents:[{parts:[{text:$p}]}]}')" \
  | jq -r '.candidates[0].content.parts[0].text'
