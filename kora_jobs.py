import os
import sys
import json
import time
import signal
import subprocess
from pathlib import Path

BASE = Path.home() / "kora"
JOBS = BASE / "jobs"
LOGS = BASE / "logs"
JOBS.mkdir(parents=True, exist_ok=True)
LOGS.mkdir(parents=True, exist_ok=True)

def job_meta_path(job_id: str) -> Path:
    return JOBS / f"{job_id}.json"

def job_log_path(job_id: str) -> Path:
    return LOGS / f"{job_id}.log"

def load_meta(job_id: str) -> dict:
    p = job_meta_path(job_id)
    if not p.exists():
        return {}
    return json.loads(p.read_text())

def save_meta(job_id: str, data: dict) -> None:
    job_meta_path(job_id).write_text(json.dumps(data, indent=2))

def start_job(job_id: str, cmd: str, cwd: str | None = None) -> dict:
    meta = load_meta(job_id)
    if meta.get("status") == "running":
        return {"ok": False, "error": f"job {job_id} is already running"}

    log_file = job_log_path(job_id)
    log_handle = open(log_file, "ab")

    proc = subprocess.Popen(
        cmd,
        shell=True,
        cwd=cwd or str(BASE),
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        preexec_fn=os.setsid,
    )

    data = {
        "job_id": job_id,
        "status": "running",
        "pid": proc.pid,
        "cmd": cmd,
        "cwd": cwd or str(BASE),
        "log": str(log_file),
        "started_at": int(time.time()),
    }
    save_meta(job_id, data)
    return {"ok": True, **data}

def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False

def status_job(job_id: str) -> dict:
    meta = load_meta(job_id)
    if not meta:
        return {"ok": False, "error": f"job {job_id} not found"}

    pid = meta.get("pid")
    if meta.get("status") == "running" and pid and not pid_alive(pid):
        meta["status"] = "finished"
        meta["ended_at"] = int(time.time())
        save_meta(job_id, meta)

    return {"ok": True, **meta}

def stop_job(job_id: str) -> dict:
    meta = load_meta(job_id)
    if not meta:
        return {"ok": False, "error": f"job {job_id} not found"}

    pid = meta.get("pid")
    if not pid:
        return {"ok": False, "error": f"job {job_id} has no pid"}

    try:
        os.killpg(os.getpgid(pid), signal.SIGTERM)
        meta["status"] = "stopped"
        meta["ended_at"] = int(time.time())
        save_meta(job_id, meta)
        return {"ok": True, **meta}
    except ProcessLookupError:
        meta["status"] = "finished"
        meta["ended_at"] = int(time.time())
        save_meta(job_id, meta)
        return {"ok": True, **meta}

def list_jobs() -> dict:
    out = []
    for p in sorted(JOBS.glob("*.json")):
        job_id = p.stem
        out.append(status_job(job_id))
    return {"ok": True, "jobs": out}

def tail_job(job_id: str, n: int = 40) -> dict:
    log = job_log_path(job_id)
    if not log.exists():
        return {"ok": False, "error": f"log for {job_id} not found"}
    lines = log.read_text(errors="ignore").splitlines()
    return {"ok": True, "job_id": job_id, "lines": lines[-n:]}

def usage():
    print("usage:")
    print("  python3 kora_jobs.py start <job_id> <command>")
    print("  python3 kora_jobs.py status <job_id>")
    print("  python3 kora_jobs.py stop <job_id>")
    print("  python3 kora_jobs.py list")
    print("  python3 kora_jobs.py tail <job_id> [n]")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)

    action = sys.argv[1]

    if action == "start" and len(sys.argv) >= 4:
        print(json.dumps(start_job(sys.argv[2], " ".join(sys.argv[3:])), indent=2))
    elif action == "status" and len(sys.argv) >= 3:
        print(json.dumps(status_job(sys.argv[2]), indent=2))
    elif action == "stop" and len(sys.argv) >= 3:
        print(json.dumps(stop_job(sys.argv[2]), indent=2))
    elif action == "list":
        print(json.dumps(list_jobs(), indent=2))
    elif action == "tail" and len(sys.argv) >= 3:
        n = int(sys.argv[3]) if len(sys.argv) >= 4 else 40
        print(json.dumps(tail_job(sys.argv[2], n), indent=2))
    else:
        usage()
        sys.exit(1)
