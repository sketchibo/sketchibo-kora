#!/usr/bin/env bash
set -u

KORA_DIR="$HOME/kora"
LOG_DIR="$KORA_DIR/logs"
OLLAMA_LOG="$LOG_DIR/ollama.log"

mkdir -p "$LOG_DIR"
cd "$KORA_DIR" || exit 1

echo "=== KORA INTERACTIVE BOOT ==="
echo "KORA_DIR: $KORA_DIR"
echo "LOG_DIR:  $LOG_DIR"

if pgrep -f "ollama serve" >/dev/null 2>&1; then
    echo "[OK] Ollama already running"
else
    echo "[BOOT] Starting Ollama..."
    nohup ollama serve > "$OLLAMA_LOG" 2>&1 &
    sleep 4
fi

if curl -s http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    echo "[OK] Ollama responding on 127.0.0.1:11434"
else
    echo "[FAIL] Ollama not responding"
    echo "Check: $OLLAMA_LOG"
    exit 1
fi

echo "[BOOT] Launching KORA in interactive mode..."
exec python3 "$KORA_DIR/kora.py"
