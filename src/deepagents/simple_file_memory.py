# src/deepagents/simple_file_memory.py
import os, json, time
from typing import List, Dict, Any

MEM_DIR = os.getenv("MEMORY_DIR", "./mem_store")
os.makedirs(MEM_DIR, exist_ok=True)

def _path(session_id: str) -> str:
    safe = "".join(c for c in session_id if c.isalnum() or c in ("-", "_"))
    return os.path.join(MEM_DIR, f"{safe}.jsonl")

def save_memory(session_id: str, role: str, content: str) -> None:
    rec = {"role": role, "content": content, "ts": time.time()}
    with open(_path(session_id), "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def load_memory(session_id: str, last_n: int = 10) -> List[Dict[str, Any]]:
    p = _path(session_id)
    if not os.path.exists(p):
        return []
    with open(p, "r", encoding="utf-8") as f:
        rows = f.readlines()
    out: List[Dict[str, Any]] = []
    for ln in rows[-last_n:]:
        ln = ln.strip()
        if not ln:
            continue
        try:
            out.append(json.loads(ln))
        except Exception:
            continue
    return out

def clear_memory(session_id: str) -> None:
    p = _path(session_id)
    try:
        os.remove(p)
    except FileNotFoundError:
        pass
