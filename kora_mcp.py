#!/usr/bin/env python3
"""
KORA MCP Server - gives Claude CLI hands on the VPS
Exposes: shell_exec, file_read, file_write
Run: python3 ~/kora/kora_mcp.py
Then in Claude CLI: connect to http://100.95.0.101:7777
"""
from flask import Flask, request, jsonify
import subprocess, os

app = Flask(__name__)
KORA_DIR = os.path.expanduser("~/kora")

@app.route("/tools", methods=["GET"])
def tools():
    return jsonify({"tools": [
        {"name": "shell_exec", "description": "Run a bash command on the KORA VPS", "parameters": {"cmd": "string"}},
        {"name": "file_read",  "description": "Read a file on the KORA VPS",        "parameters": {"path": "string"}},
        {"name": "file_write", "description": "Write content to a file on the VPS", "parameters": {"path": "string", "content": "string"}},
    ]})

@app.route("/call", methods=["POST"])
def call():
    body = request.json
    tool = body.get("tool")
    args = body.get("args", {})
    if tool == "shell_exec":
        result = subprocess.run(args["cmd"], shell=True, capture_output=True, text=True, timeout=30, cwd=KORA_DIR)
        return jsonify({"stdout": result.stdout, "stderr": result.stderr, "rc": result.returncode})
    elif tool == "file_read":
        try:
            return jsonify({"content": open(os.path.expanduser(args["path"])).read()})
        except Exception as e:
            return jsonify({"error": str(e)})
    elif tool == "file_write":
        try:
            path = os.path.expanduser(args["path"])
            open(path, "w").write(args["content"])
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"error": str(e)})
    return jsonify({"error": "unknown tool"})

if __name__ == "__main__":
    print("KORA MCP online at http://100.95.0.101:7777")
    app.run(host="0.0.0.0", port=7777)
