#!/usr/bin/env bash
set -euo pipefail

if [ -z "${GEMINI_API_KEY:-}" ]; then
  echo "GEMINI_API_KEY is not set"
  exit 1
fi

PROMPT="${1:-Say: KORA bridge is online.}"

curl -sS \
  -H "Content-Type: application/json" \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${GEMINI_API_KEY}" \
  -d "$(printf '{"contents":[{"parts":[{"text":"%s"}]}]}' "$PROMPT")"
