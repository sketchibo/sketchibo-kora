#!/usr/bin/env python3
"""
kora_server.py — HTTP API server for KORA
Bridges Android app to Kora's ReAct loop
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent to path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

# Import from terminal
from kora_terminal import (
    agent_turn, load_startup_context, load_chat_history, save_exchange,
    load_identity_core_cached, load_handoffs, console, build_system
)

# Try Flask, fall back to http.server
try:
    from flask import Flask, request, jsonify
    FLASK_MODE = True
except ImportError:
    FLASK_MODE = False
    from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = int(os.getenv('KORA_PORT', '5000'))

# Load system context once at startup
SYSTEM_CONTEXT = build_system(load_startup_context())
HISTORY = [{'role': 'system', 'content': SYSTEM_CONTEXT}]

def get_reply_text(text: str) -> dict:
    """Process a command and return reply + optional action."""
    global HISTORY
    
    try:
        new_msgs = agent_turn(HISTORY, text, prefer_online=True, quick_mode=False)
        HISTORY.extend(new_msgs)
        
        # Keep history bounded
        if len(HISTORY) > 40:
            HISTORY = [HISTORY[0]] + HISTORY[-30:]
        
        # Extract assistant reply
        assistant_reply = next(
            (m['content'] for m in reversed(new_msgs) if m['role'] == 'assistant'),
            'No response generated.'
        )
        
        # Persist
        save_exchange(text, assistant_reply)
        
        # Check for action intents in reply
        action = None
        if 'open ' in text.lower() or 'launch ' in text.lower():
            # Simple app opening detection
            for app in ['termux', 'chrome', 'settings', 'files']:
                if app in text.lower():
                    action = {
                        'type': 'open_app',
                        'package': f'com.{app}' if app != 'chrome' else 'com.android.chrome'
                    }
                    break
        
        return {
            'reply_text': assistant_reply,
            'action': action,
            'model_used': 'kora-local'
        }
        
    except Exception as e:
        return {
            'reply_text': f'Error: {str(e)}',
            'action': None,
            'error': str(e)
        }


if FLASK_MODE:
    app = Flask(__name__)
    
    @app.route('/')
    def index():
        return jsonify({
            'status': 'KORA server running',
            'endpoints': ['/command', '/health'],
            'version': '2026.04.05'
        })
    
    @app.route('/health')
    def health():
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat()
        })
    
    @app.route('/command', methods=['POST'])
    def command():
        data = request.get_json() or {}
        text = data.get('text', '')
        if not text:
            return jsonify({'error': 'Missing text field'}), 400
        
        result = get_reply_text(text)
        return jsonify(result)
    
    @app.route('/memory', methods=['GET'])
    def memory():
        """Get recent facts."""
        from kora_terminal import load_recent_facts
        facts = load_recent_facts(10)
        return jsonify({'facts': facts})

else:
    # Fallback to http.server
    class KoraHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # Suppress logs
        
        def do_GET(self):
            if self.path == '/':
                self.send_json({
                    'status': 'KORA server running (http.server fallback)',
                    'endpoints': ['/command', '/health']
                })
            elif self.path == '/health':
                self.send_json({
                    'status': 'healthy',
                    'timestamp': datetime.now().isoformat()
                })
            else:
                self.send_error(404)
        
        def do_POST(self):
            if self.path == '/command':
                content_len = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_len).decode()
                try:
                    data = json.loads(body)
                    text = data.get('text', '')
                    result = get_reply_text(text)
                    self.send_json(result)
                except Exception as e:
                    self.send_json({'error': str(e)}, 500)
            else:
                self.send_error(404)
        
        def send_json(self, data, status=200):
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())


def main():
    print(f"[KORA SERVER] Starting on port {PORT}")
    print(f"[KORA SERVER] Endpoint: http://127.0.0.1:{PORT}/command")
    print(f"[KORA SERVER] Health:   http://127.0.0.1:{PORT}/health")
    print(f"[KORA SERVER] Mode:     {'Flask' if FLASK_MODE else 'http.server'}")
    print()
    
    if FLASK_MODE:
        # Flask mode - threaded, production-ready
        app.run(host='0.0.0.0', port=PORT, threaded=True, debug=False)
    else:
        # Fallback mode
        server = HTTPServer(('0.0.0.0', PORT), KoraHandler)
        print(f"[KORA SERVER] Running... Press Ctrl+C to stop")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n[KORA SERVER] Stopping...")
            server.shutdown()


if __name__ == '__main__':
    main()
