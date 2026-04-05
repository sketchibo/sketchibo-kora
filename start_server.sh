#!/bin/bash
# Start KORA server for Android bridge

echo "[KORA] Starting HTTP server..."
echo "[KORA] Android app will connect to localhost:5000"
echo "[KORA] Press Ctrl+C to stop"
echo ""

# Check if Flask available, install if not
python3 -c "import flask" 2>/dev/null || pip install flask --quiet

# Start server
python3 ~/kora_local/kora_server.py
