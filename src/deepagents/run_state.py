# src/deepagents/run_state.py
"""
运行时状态 / ToDo / 校验 / 持久化
- create_run_state(): 新建一次运行（生成 trace_id、todo、action_guess）
- append_step():      追加步骤记录
- set_todo_status():  更新 ToDo 某一步的状态
- validate_output():  结果校验（只返回最终结果、JSON 合法性、长度）
- set_validation():   保存校验结论
- load_state():       读取某次运行的完整状态
- list_states():      列出最近运行摘要
- configure_runtime():配置并确保 run_dir / mem_dir 存在
- get_runtime_dirs(): 返回当前目录（健康检查用）
"""
import os
import json
import uuid
import time
from typing import Any, Dict, List, Optional, Tuple

# ------------ 目录配置 ------------
RUN_DIR = os.getenv("RUN_DIR", "./run_store")
MEM_DIR = os.getenv("MEMORY_DIR", "./mem_store")

def configure_runtime(run_dir: Optional[str] = None, mem_dir: Optional[str] = None) -> None:
    """在应用启动时调用，覆盖默认目录并确保存在。"""
    global RUN_DIR, MEM_DIR
    if run_dir:
        RUN_DIR = run_dir
    if mem_dir:
        MEM_DIR = mem_dir
    os.makedirs(RUN_DIR, exist_ok=True)
    os.makedirs(MEM_DIR, exist_ok=True)

# 确保目录存在
configure_runtime(RUN_DIR, MEM_DIR)

# ------------ 内部工具 ------------
def _now_iso() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

def _run_path(trace_id: str) -> str:
    return os.path.join(RUN_DIR, f"{trace_id}.json")

def _save_state(state: Dict[str, Any]) -> None:
    with open(_run_path(state["trace_id"]), "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, default=str)

def _load_state(trace_id: str) -> Dict[str, Any]:
    p = _run_path(trace_id)
    if not os.path.exists(p):
        raise FileNotFoundError("trace_id not found")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

# ------------ 动作猜测 ------------
def _guess_action(user_input: str) -> str:
    text = user_input.lower()
    if ("推荐" in user_input) or ("推荐信" in user_input):
        return "generate_recommendation"
    if ("陈述" in user_input) or ("ps" in text) or ("statement" in text):
        return "generate_statement"
    if ("解析" in user_input and "简历" in user_input) or ("parse" in text and "resume" in text):
        return "parse_resume_text"
    if ("精简" in user_input) or ("压缩" in user_input) or ("contract" in text):
        return "contract"
    if ("扩写" in user_input) or ("expand" in text):
        return "expand"
    if ("命名" in user_input) or ("标题" in user_input):
        return "name_document"
    return "rewrite_letter"

# ------------ 公共 API ------------
def create_run_state(session_id: str, user_input: str) -> Dict[str, Any]:
    """创建一次运行状态并落盘；返回 state（含 trace_id / todo / action_guess）"""
    trace_id = str(uuid.uuid4())
    action = _guess_action(user_input)
    state = {
        "trace_id": trace_id,
        "session_id": session_id,
        "created_at": _now_iso(),
        # 关键：不再预置固定 ToDo，交由三角色调度器动态写入（plan / step-i / step-i-validate）
        "todo": [],
        "action_guess": action,
        "steps": [],
        "validation": None,
    }
    _save_state(state)
    return state

def append_step(trace_id: str, name: str, status: str = "started", details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """追加 steps 记录并保存；返回最新 state。"""
    state = _load_state(trace_id)
    entry = {"ts": _now_iso(), "name": name, "status": status, "details": details or {}}
    state.setdefault("steps", []).append(entry)
    _save_state(state)
    return state

def set_todo_status(trace_id: str, step: str, status: str) -> Dict[str, Any]:
    """更新 ToDo 某一步的状态：pending | in_progress | completed | failed"""
    state = _load_state(trace_id)
    todo = state.get("todo") or []
    found = False
    for item in todo:
        if item.get("step") == step:
            item["status"] = status
            found = True
            break
    if not found:
        # 如果没有该 step，自动追加一条（防御性容错）
        todo.append({"step": step, "desc": "", "status": status})
    state["todo"] = todo
    _save_state(state)
    return state

def validate_output(action: str, output: str) -> Tuple[bool, List[str]]:
    """基础校验：只返回最终结果；必要时 JSON 合法；长度限制。"""
    issues: List[str] = []
    out = output if isinstance(output, str) else str(output)

    if not out.strip():
        issues.append("输出为空")

    # 禁止解释/过程性内容（可按需扩展关键词）
    explain_markers = ["以下是", "Explanation", "解析：", "步骤：", "过程：", "我将", "我会", "工具调用"]
    if any(m in out for m in explain_markers):
        issues.append("包含解释性或过程性文字")

    # JSON 动作的基本校验
    if action == "parse_resume_text":
        try:
            json.loads(out)
        except Exception:
            issues.append("action=parse_resume_text 但输出不是合法 JSON")

    # 长度限制
    max_len = int(os.getenv("MAX_OUTPUT_CHARS", "20000"))
    if len(out) > max_len:
        issues.append(f"输出过长（>{max_len} 字符）")

    return (len(issues) == 0), issues

def set_validation(trace_id: str, ok: bool, issues: List[str]) -> Dict[str, Any]:
    """保存校验结果并落盘；返回最新 state。"""
    state = _load_state(trace_id)
    state["validation"] = {"ok": ok, "issues": issues, "ts": _now_iso()}
    _save_state(state)
    return state

def load_state(trace_id: str) -> Dict[str, Any]:
    """读取某次运行的完整状态"""
    return _load_state(trace_id)

def list_states(session_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """列出运行摘要（时间倒序）。"""
    items: List[Dict[str, Any]] = []
    for fn in os.listdir(RUN_DIR):
        if not fn.endswith(".json"):
            continue
        p = os.path.join(RUN_DIR, fn)
        try:
            with open(p, "r", encoding="utf-8") as f:
                s = json.load(f)
            if (session_id is None) or (s.get("session_id") == session_id):
                items.append({
                    "trace_id": s.get("trace_id"),
                    "session_id": s.get("session_id"),
                    "created_at": s.get("created_at"),
                    "action_guess": s.get("action_guess"),
                    "validation": s.get("validation", {}),
                })
        except Exception:
            continue
    items.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return items

def get_runtime_dirs() -> Dict[str, str]:
    """返回当前运行目录（健康检查用）"""
    return {"run_dir": RUN_DIR, "mem_dir": MEM_DIR}
