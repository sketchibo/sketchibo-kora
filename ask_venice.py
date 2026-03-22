#!/usr/bin/env python3
import sys
from kora import venice_chat

def main():
    snapshot = sys.stdin.read().strip()
    if not snapshot:
        print("[ERROR] No snapshot provided.")
        raise SystemExit(1)

    prompt = f"""Here is a self-snapshot from an AI system called KORA.

Please answer:
1. What is KORA?
2. What architecture does it resemble?
3. What are its strengths?
4. What are its weaknesses?
5. What should it evolve into next?

Snapshot:
{snapshot}
"""

    reply = venice_chat(prompt, timeout=60)
    print(reply or "[ERROR] Venice returned no reply.")

if __name__ == "__main__":
    main()
