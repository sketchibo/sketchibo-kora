#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-local}"
shift || true
PROMPT="${*:-Say: KORA is online.}"

LOCAL_MODEL="${LOCAL_MODEL:-qwen2.5:7b}"

ask_local() {
  curl -s http://127.0.0.1:11434/api/generate \
    -d "$(jq -nc --arg model "$LOCAL_MODEL" --arg prompt "$PROMPT" \
      '{model:$model,prompt:$prompt,stream:false}')"
}

ask_cloud() {
  if [ -z "${GEMINI_API_KEY:-}" ]; then
    echo "GEMINI_API_KEY is not set"
    exit 1
  fi

  curl -sS \
    -H "Content-Type: application/json" \
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${GEMINI_API_KEY}" \
    -d "$(jq -nc --arg p "$PROMPT" '{contents:[{parts:[{text:$p}]}]}')"
}

case "$MODE" in
  local)
    ask_local | jq -r '.response'
    ;;
  cloud)
    ask_cloud | jq -r '.candidates[0].content.parts[0].text'
    ;;
  both)
    LOCAL_TEXT="$(ask_local | jq -r '.response')"
    if [ -z "${GEMINI_API_KEY:-}" ]; then
      echo "$LOCAL_TEXT"
      exit 0
    fi

    REFINE_PROMPT=$(cat <<TXT
User prompt:
$PROMPT

Local Dolphin answer:
$LOCAL_TEXT

Refine or improve that answer briefly.
TXT
)
    curl -sS \
      -H "Content-Type: application/json" \
      "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${GEMINI_API_KEY}" \
      -d "$(jq -nc --arg p "$REFINE_PROMPT" '{contents:[{parts:[{text:$p}]}]}')" \
      | jq -r '.candidates[0].content.parts[0].text'
    ;;
  *)
    echo "Usage: $0 {local|cloud|both} your prompt here"
    exit 1
    ;;
esac
