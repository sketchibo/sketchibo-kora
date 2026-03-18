#!/data/data/com.termux/files/usr/bin/bash
#!/usr/bin/env bash

set -u

KORA_DIR="$HOME/kora"
LOG_DIR="$KORA_DIR/logs"
OLLAMA_LOG="$LOG_DIR/ollama.log"
KORA_LOG="$LOG_DIR/kora.log"

mkdir -p "$LOG_DIR"

cd "$KORA_DIR" || exit 1

echo "=== KORA BOOT ==="
echo "KORA_DIR: $KORA_DIR"
echo "LOG_DIR:  $LOG_DIR"

# 1. Start Ollama if not already running
if pgrep -f "ollama serve" >/dev/null 2>&1; then
    echo "[OK] Ollama already running"
else
    echo "[BOOT] Starting Ollama..."
    nohup ollama serve > "$OLLAMA_LOG" 2>&1 &
    sleep 4
fi

# 2. Check Ollama API
if curl -s http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    echo "[OK] Ollama responding on 127.0.0.1:11434"
else
    echo "[FAIL] Ollama not responding"
    echo "Check: $OLLAMA_LOG"
    exit 1
fi

# 3. Stop old KORA if already running
if pgrep -f "python3 kora.py" >/dev/null 2>&1; then
    echo "[WARN] Existing KORA found, stopping old instance..."
    pkill -f "python3 kora.py"
    sleep 2
fi

# 4. Start KORA
echo "[BOOT] Starting KORA..."
nohup python3 "$KORA_DIR/kora.py" > "$KORA_LOG" 2>&1 &
sleep 2

# 5. Verify KORA process
if pgrep -f "python3 kora.py" >/dev/null 2>&1; then
    echo "[OK] KORA is running"
else
    echo "[FAIL] KORA failed to start"
    echo "Check: $KORA_LOG"
    exit 1
fi

echo
echo "=== KORA ONLINE ==="
echo "Ollama log: $OLLAMA_LOG"
echo "KORA log:   $KORA_LOG"
echo
echo "Diagnostics:"
echo "  curl http://127.0.0.1:11434/api/tags"
echo "  tail -f $OLLAMA_LOG"
echo "  tail -f $KORA_LOG"

