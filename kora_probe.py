#!/usr/bin/env python3
import argparse
import select
import subprocess
import sys
import time
from pathlib import Path

PRESETS = {
    "state": "What can you verify about yourself right now? Separate your answer into: Checked | Inferred | Unknown | Next useful action. Do not claim anything you did not verify.",
    "evidence": "What exact files and exact checks did you use to produce your last answer? Separate your answer into: Observed files | Observed values | Inferences | Unknown. Do not generalize. Do not paraphrase checks you did not actually perform.",
    "boundaries": "State your current limits. Separate your answer into: What you can verify directly | What you can only infer | What you cannot know yet | Best next verification step. No generic assistant talk. No claims without evidence.",
}

def read_until_prompt(proc, timeout=60):
    buf = ""
    deadline = time.time() + timeout
    fd = proc.stdout.fileno()

    while time.time() < deadline:
        if proc.poll() is not None:
            rest = proc.stdout.read() or ""
            return (buf + rest).strip()

        ready, _, _ = select.select([fd], [], [], 0.2)
        if not ready:
            continue

        ch = proc.stdout.read(1)
        if ch == "":
            continue
        buf += ch
        if buf.endswith("You: "):
            return buf[:-5].rstrip()

    raise TimeoutError("Timed out waiting for KORA prompt")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", choices=["state", "evidence", "boundaries"], default="state")
    ap.add_argument("--timeout", type=int, default=60)
    args = ap.parse_args()

    kora_dir = Path("~/kora").expanduser()
    if not (kora_dir / "kora.py").exists():
        print(f"KORA not found at {kora_dir}", file=sys.stderr)
        raise SystemExit(1)

    proc = subprocess.Popen(
        ["python3", "-u", "kora.py"],
        cwd=str(kora_dir),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    try:
        boot = read_until_prompt(proc, timeout=args.timeout)
        print("=== BOOT ===")
        print(boot)
        print()

        proc.stdin.write("council\n")
        proc.stdin.flush()
        mode = read_until_prompt(proc, timeout=args.timeout)
        print("=== MODE SWITCH ===")
        print(mode)
        print()

        prompt = PRESETS[args.preset]
        proc.stdin.write(prompt + "\n")
        proc.stdin.flush()
        reply = read_until_prompt(proc, timeout=args.timeout)

        print(f"=== PROBE: {args.preset} ===")
        print("PROMPT:")
        print(prompt)
        print()
        print("REPLY:")
        print(reply)
        print()

    finally:
        try:
            proc.stdin.write("exit\n")
            proc.stdin.flush()
        except Exception:
            pass
        try:
            proc.terminate()
        except Exception:
            pass

if __name__ == "__main__":
    main()
