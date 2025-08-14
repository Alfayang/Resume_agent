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

# 内存中的任务状态管理
import threading
from typing import Dict, Any, Optional

# 全局内存状态存储
_memory_states: Dict[str, Dict[str, Any]] = {}
_memory_lock = threading.Lock()

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
    """保存状态到JSON文件，支持增量更新"""
    file_path = _run_path(state["trace_id"])
    
    # 如果文件不存在，直接写入
    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2, default=str)
        return
    
    # 如果文件存在，尝试增量更新
    try:
        # 读取现有状态
        with open(file_path, "r", encoding="utf-8") as f:
            existing_state = json.load(f)
        
        # 合并状态（新状态覆盖旧状态）
        merged_state = {**existing_state, **state}
        
        # 特殊处理steps数组：追加而不是覆盖
        if "steps" in state and "steps" in existing_state:
            # 获取新的steps
            new_steps = state["steps"]
            existing_steps = existing_state["steps"]
            
            # 如果新steps是现有steps的扩展，则合并
            if len(new_steps) >= len(existing_steps):
                # 检查是否只是追加了新步骤
                if new_steps[:len(existing_steps)] == existing_steps:
                    merged_state["steps"] = new_steps
                else:
                    # 如果有变化，使用新状态
                    merged_state["steps"] = new_steps
            else:
                # 如果新steps更短，保持现有状态
                merged_state["steps"] = existing_steps
        
        # 写入合并后的状态
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(merged_state, f, ensure_ascii=False, indent=2, default=str)
            
    except Exception as e:
        # 如果增量更新失败，回退到完整重写
        print(f"增量更新失败，回退到完整重写: {e}")
        with open(file_path, "w", encoding="utf-8") as f:
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
def create_run_state(session_id: Optional[str], user_input: str) -> Dict[str, Any]:
    """创建新的运行状态"""
    trace_id = str(uuid.uuid4())
    
    # 创建内存状态
    memory_state = create_memory_state(trace_id, session_id, user_input)
    
    # 创建文件状态（异步，不阻塞）
    def _create_file_state():
        try:
            state = {
                "trace_id": trace_id,
                "session_id": session_id,
                "user_input": user_input,
                "created_at": time.time(),
                "todo": [],
                "steps": [],
                "validation": {"ok": False, "status": "pending"},
                "plan_rationale": "正在初始化任务..."
            }
            
            state_file = os.path.join(RUN_DIR, f"{trace_id}.json")
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            
            print(f"📁 创建文件状态: {state_file}")
        except Exception as e:
            print(f"❌ 创建文件状态失败: {e}")
    
    # 在后台线程中创建文件状态
    import threading
    threading.Thread(target=_create_file_state, daemon=True).start()
    
    return memory_state

def append_step(trace_id: str, name: str, status: str = "started", details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """追加一个执行步骤"""
    step = {
        "name": name,
        "status": status,
        "ts": _now_iso(),
        "details": details or {}
    }
    
    # 更新内存状态
    memory_state = get_memory_state(trace_id)
    if memory_state:
        if "steps" not in memory_state:
            memory_state["steps"] = []
        memory_state["steps"].append(step)
        update_memory_state(trace_id, {"steps": memory_state["steps"]})
    
    # 更新文件状态（异步）
    def _update_file_state():
        try:
            state = _load_state(trace_id)
            if "steps" not in state:
                state["steps"] = []
            state["steps"].append(step)
            _save_state(state)
        except Exception as e:
            print(f"❌ 更新文件状态失败: {e}")
    
    # 在后台线程中更新文件状态
    import threading
    threading.Thread(target=_update_file_state, daemon=True).start()
    
    return step

def set_todo_status(trace_id: str, step: str, status: str) -> Dict[str, Any]:
    """设置 ToDo 状态"""
    # 更新内存状态
    memory_state = get_memory_state(trace_id)
    if memory_state:
        if "todo" not in memory_state:
            memory_state["todo"] = []
        
        # 查找或创建todo项
        todo_item = None
        for item in memory_state["todo"]:
            if item.get("step") == step:
                todo_item = item
                break
        
        if not todo_item:
            todo_item = {"step": step, "status": status, "desc": f"步骤: {step}"}
            memory_state["todo"].append(todo_item)
        else:
            todo_item["status"] = status
        
        update_memory_state(trace_id, {"todo": memory_state["todo"]})
    
    # 更新文件状态（异步）
    def _update_file_state():
        try:
            state = _load_state(trace_id)
            if "todo" not in state:
                state["todo"] = []
            
            # 查找或创建todo项
            todo_item = None
            for item in state["todo"]:
                if item.get("step") == step:
                    todo_item = item
                    break
            
            if not todo_item:
                todo_item = {"step": step, "status": status, "desc": f"步骤: {step}"}
                state["todo"].append(todo_item)
            else:
                todo_item["status"] = status
            
            _save_state(state)
        except Exception as e:
            print(f"❌ 更新文件todo状态失败: {e}")
    
    # 在后台线程中更新文件状态
    import threading
    threading.Thread(target=_update_file_state, daemon=True).start()
    
    return {"step": step, "status": status}

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

def set_validation(trace_id: str, ok: bool, feedback: Optional[List[str]] = None) -> Dict[str, Any]:
    """设置验证结果"""
    validation = {
        "ok": ok,
        "status": "completed" if ok else "failed",
        "feedback": feedback or []
    }
    
    # 更新内存状态
    update_memory_state(trace_id, {"validation": validation})
    
    # 更新文件状态（异步）
    def _update_file_state():
        try:
            state = _load_state(trace_id)
            state["validation"] = validation
            _save_state(state)
        except Exception as e:
            print(f"❌ 更新文件验证状态失败: {e}")
    
    # 在后台线程中更新文件状态
    import threading
    threading.Thread(target=_update_file_state, daemon=True).start()
    
    return validation

def load_state(trace_id: str) -> Dict[str, Any]:
    """加载运行状态（优先从内存，其次从文件）"""
    # 首先尝试从内存加载
    memory_state = get_memory_state(trace_id)
    if memory_state:
        return memory_state
    
    # 如果内存中没有，从文件加载
    state_file = os.path.join(RUN_DIR, f"{trace_id}.json")
    if not os.path.exists(state_file):
        raise FileNotFoundError(f"状态文件不存在: {state_file}")
    
    try:
        with open(state_file, "r", encoding="utf-8") as f:
            state = json.load(f)
        
        # 将文件状态同步到内存
        update_memory_state(trace_id, state)
        return state
    except Exception as e:
        raise RuntimeError(f"加载状态失败: {e}")

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

def create_memory_state(trace_id: str, session_id: Optional[str], user_input: str) -> Dict[str, Any]:
    """在内存中创建任务状态"""
    with _memory_lock:
        initial_state = {
            "trace_id": trace_id,
            "session_id": session_id,
            "user_input": user_input,
            "created_at": time.time(),
            "todo": [],
            "steps": [],
            "validation": {"ok": False, "status": "pending"},
            "plan_rationale": "正在初始化任务..."
        }
        _memory_states[trace_id] = initial_state
        print(f"📝 在内存中创建任务状态: {trace_id}")
        return initial_state

def update_memory_state(trace_id: str, updates: Dict[str, Any]) -> None:
    """更新内存中的任务状态"""
    with _memory_lock:
        if trace_id in _memory_states:
            _memory_states[trace_id].update(updates)
            print(f"📝 更新内存任务状态: {trace_id} - {list(updates.keys())}")

def get_memory_state(trace_id: str) -> Optional[Dict[str, Any]]:
    """获取内存中的任务状态"""
    with _memory_lock:
        return _memory_states.get(trace_id)

def remove_memory_state(trace_id: str) -> None:
    """移除内存中的任务状态"""
    with _memory_lock:
        if trace_id in _memory_states:
            del _memory_states[trace_id]
            print(f"🗑️ 移除内存任务状态: {trace_id}")

def list_memory_states() -> Dict[str, Dict[str, Any]]:
    """列出所有内存中的任务状态"""
    with _memory_lock:
        return _memory_states.copy()
