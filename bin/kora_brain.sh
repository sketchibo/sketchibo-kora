#!/usr/bin/env bash

PROMPT="$*"

[ -z "$PROMPT" ] && echo "Usage: kora_brain \"your prompt\"" && exit 1

curl -s http://127.0.0.1:11434/api/generate \
  -d "{
    \"model\": \"qwen2.5:7b\",
    \"prompt\": \"$PROMPT\",
    \"stream\": false
  }" | jq -r .response | tee -a ~/kora/logs/brain.log

