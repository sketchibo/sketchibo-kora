import os
import fnmatch
from pathlib import Path
from typing import List, Dict, Any


BASE_DIR = Path.home() / "kora"


def _safe_resolve(path: str = ".") -> Path:
    """
    Resolve paths relative to ~/kora and prevent escaping outside it.
    """
    candidate = (BASE_DIR / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()

    if not str(candidate).startswith(str(BASE_DIR.resolve())):
        raise ValueError(f"Refusing path outside BASE_DIR: {candidate}")

    return candidate


def list_files(path: str = ".") -> Dict[str, Any]:
    target = _safe_resolve(path)
    if not target.exists():
        return {"ok": False, "error": f"Path does not exist: {target}"}
    if not target.is_dir():
        return {"ok": False, "error": f"Not a directory: {target}"}

    items = []
    for entry in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        items.append({
            "name": entry.name,
            "type": "dir" if entry.is_dir() else "file",
            "path": str(entry.relative_to(BASE_DIR))
        })

    return {"ok": True, "path": str(target.relative_to(BASE_DIR)), "items": items}


def read_file(path: str, max_chars: int = 12000) -> Dict[str, Any]:
    target = _safe_resolve(path)
    if not target.exists():
        return {"ok": False, "error": f"File does not exist: {target}"}
    if not target.is_file():
        return {"ok": False, "error": f"Not a file: {target}"}

    try:
        content = target.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return {"ok": False, "error": f"Failed reading file: {e}"}

    truncated = False
    if len(content) > max_chars:
        content = content[:max_chars]
        truncated = True

    return {
        "ok": True,
        "path": str(target.relative_to(BASE_DIR)),
        "content": content,
        "truncated": truncated
    }


def tail_file(path: str, lines: int = 80) -> Dict[str, Any]:
    target = _safe_resolve(path)
    if not target.exists():
        return {"ok": False, "error": f"File does not exist: {target}"}
    if not target.is_file():
        return {"ok": False, "error": f"Not a file: {target}"}

    try:
        content = target.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception as e:
        return {"ok": False, "error": f"Failed reading file: {e}"}

    tail = "\n".join(content[-lines:])
    return {
        "ok": True,
        "path": str(target.relative_to(BASE_DIR)),
        "lines": lines,
        "content": tail
    }


def search_files(query: str, root: str = ".", pattern: str = "*", max_hits: int = 25) -> Dict[str, Any]:
    base = _safe_resolve(root)
    if not base.exists():
        return {"ok": False, "error": f"Root does not exist: {base}"}
    if not base.is_dir():
        return {"ok": False, "error": f"Root is not a directory: {base}"}

    hits: List[Dict[str, Any]] = []
    q = query.lower()

    for dirpath, _, filenames in os.walk(base):
        for filename in filenames:
            if not fnmatch.fnmatch(filename, pattern):
                continue

            full_path = Path(dirpath) / filename
            try:
                text = full_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            lower_text = text.lower()
            if q in lower_text or q in filename.lower():
                idx = lower_text.find(q) if q in lower_text else -1
                snippet = ""
                if idx >= 0:
                    start = max(0, idx - 120)
                    end = min(len(text), idx + len(query) + 220)
                    snippet = text[start:end].replace("\n", " ")

                hits.append({
                    "path": str(full_path.relative_to(BASE_DIR)),
                    "snippet": snippet
                })

                if len(hits) >= max_hits:
                    return {
                        "ok": True,
                        "query": query,
                        "root": str(base.relative_to(BASE_DIR)),
                        "hits": hits,
                        "truncated": True
                    }

    return {
        "ok": True,
        "query": query,
        "root": str(base.relative_to(BASE_DIR)),
        "hits": hits,
        "truncated": False
    }


def get_system_status() -> Dict[str, Any]:
    import platform
    import shutil

    total, used, free = shutil.disk_usage(str(BASE_DIR))
    return {
        "ok": True,
        "base_dir": str(BASE_DIR),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "cwd_exists": BASE_DIR.exists(),
        "disk_total_gb": round(total / (1024**3), 2),
        "disk_used_gb": round(used / (1024**3), 2),
        "disk_free_gb": round(free / (1024**3), 2),
    }
