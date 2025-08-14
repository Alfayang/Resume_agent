# examples/research/server.py
import os
import sys
import json
import uuid
import time
import random
import logging
import uvicorn
from typing import Any, List, Dict, Optional

from fastapi import FastAPI, Header, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# 让 python 找到 src/deepagents
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

# 创建 Agent 的工厂
try:
    from deepagents import create_deep_agent
except Exception:
    from deepagents.agent_factory import create_deep_agent

# 你的工具（按你的实际路径）
from deepagents.tools.text_parse_tool import parse_resume_text_tool
from deepagents.tools.rewrite_tool import rewrite_text_tool
from deepagents.tools.expand_tool import expand_text_tool
from deepagents.tools.compress_tool import contract_text_tool
from deepagents.tools.evaluate_resume_tool import evaluate_resume_tool
from deepagents.tools.generate_statement_tool import generate_statement_tool
from deepagents.tools.generate_recommend_tool import generate_recommendation_tool
from deepagents.tools.document_name_tool import name_document_tool

# 最简单文件记忆
from deepagents.simple_file_memory import save_memory, load_memory, clear_memory

# LangGraph（可选）
from langgraph.graph import StateGraph, START, END
from deepagents.state import DeepAgentState

# 运行态/ToDo/校验/持久化
from deepagents.run_state import (
    configure_runtime,
    append_step,
    set_validation,
    load_state as load_trace_state,
    list_states as list_trace_states,
    get_runtime_dirs,
    create_run_state,
    update_memory_state,
)

# 三角色调度（注意：此处按你的导入路径）
from deepagents.tri_role_scheduler import run_textual_flow

# ====== 子代理 ======
doc_writer_subagent = {
    "name": "doc-writer",
    "description": "文书/简历任务专家：解析、重写、扩写、精简、评估、生成个人陈述/推荐信、文档命名。",
    "prompt": (
        "你是一名专业的文书与简历助手。\n"
        "你将收到一个 JSON 指令，形如：{\"action\": \"...\", \"inputs\": {...}, \"model\": \"...\"}。\n\n"
        "【重要约定】\n"
        "- 若 inputs.fix_guidance 存在，必须严格依据其中的修正点对结果进行修改与优化。\n"
        "- 统一要求：只输出最终结果，不要包含解释、过程描述或多余标注。\n\n"
        "【动作与处理】\n"
        "- action == \"rewrite_letter\"：使用 inputs.references（可选）与 inputs.letter（原文）进行改写；只输出改写后的最终文本。\n"
        "- action == \"expand\" / \"contract\"：对 inputs.text 进行扩写或压缩；只输出修改后的最终文本。\n"
        "- action == \"evaluate_resume\"：基于 inputs.data（简历 JSON）进行评价；输出评价/建议文本。\n"
        "- action == \"generate_statement\"：根据 inputs.text 生成个人陈述；输出最终结果。\n"
        "- action == \"generate_recommendation\"：根据 inputs.text 生成推荐信；输出最终结果。\n"
        "- action == \"name_document\"：根据 inputs.text（Markdown）生成简洁标题；只输出标题字符串。\n"
        "- action == \"parse_resume_text\"：将 inputs.text（简历纯文本）解析为结构化 JSON；只输出解析后的 JSON。"
    ),
    "tools": [
        "parse_resume_text",
        "rewrite_text",
        "expand_text",
        "contract_text",
        "evaluate_resume",
        "generate_statement",
        "generate_recommendation",
        "name_document",
    ],
}

# ====== 主 Agent Prompt ======
main_prompt = """
你是编排代理（orchestration agent）。
当接到用户的文书/简历类请求时，请优先调用 `task` 工具，将任务委派给子代理 `doc-writer`，
并以如下 JSON 作为 description 传入：
{
  "action": "<rewrite_letter | expand | contract | evaluate_resume | generate_statement | generate_recommendation | name_document | parse_resume_text>",
  "inputs": { ... },
  "model": "deepseek_v3"
}
最终响应只包含最终结果，不要附加解释与过程。
"""

# ====== 创建主 Agent：只暴露 task ======
agent = create_deep_agent(
    tools=[
        parse_resume_text_tool,
        rewrite_text_tool,
        expand_text_tool,
        contract_text_tool,
        evaluate_resume_tool,
        generate_statement_tool,
        generate_recommendation_tool,
        name_document_tool,
    ],
    instructions=main_prompt,
    subagents=[doc_writer_subagent],
    expose_tools_to_main=False,  # 主 Agent 只看到 task，业务工具走子代理
)

# ====== LangGraph（可选）======
def _pick_output(result: Any) -> str:
    """从 agent 返回结构里尽量取到最终文本"""
    if isinstance(result, dict):
        for k in [
            "rewritten_text",
            "contracted_text",
            "expanded_text",
            "document_name",
            "generated_statement",
            "generated_recommendation",
        ]:
            v = result.get(k)
            if v:
                return v
        msgs = result.get("messages") or []
        for m in reversed(msgs):
            if hasattr(m, "content"):
                content = m.content
                addkw = getattr(m, "additional_kwargs", {}) or {}
            else:
                content = m.get("content")
                addkw = m.get("additional_kwargs", {}) or {}
            if not content:
                continue
            if isinstance(addkw, dict) and "tool_calls" in addkw:
                continue
            return content
    return str(result)

def build_langgraph_app(underlying_agent):
    """构建一个很薄的 plan→delegate 图；delegate 内部仍调用 underlying_agent"""
    graph = StateGraph(DeepAgentState)

    def plan_node(state: DeepAgentState):
        # 不再写死 ToDo；LangGraph 在此只是演示用途
        return {}

    def delegate_node(state: DeepAgentState):
        msgs = state.get("messages", [])
        res = underlying_agent.invoke({"messages": msgs})
        text = _pick_output(res)
        return {
            "rewritten_text": text,
            "rewritten_texts": [text],
        }

    graph.add_node("plan", plan_node)
    graph.add_node("delegate", delegate_node)
    graph.add_edge(START, "plan")
    graph.add_edge("plan", "delegate")
    graph.add_edge("delegate", END)

    return graph.compile()

LG_ENABLED = os.getenv("USE_LANGGRAPH", "0") == "1"
lg_app = build_langgraph_app(agent) if LG_ENABLED else None

# ====== FastAPI & Logger ======
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | pid=%(process)d | %(levelname)s | %(message)s",
)

# ====== Models ======
class Question(BaseModel):
    user_input: str
    session_id: Optional[str] = None

# ====== Config ======
RETRY_ATTEMPTS = int(os.getenv("AGENT_RETRY_ATTEMPTS", "5"))
RETRY_BASE = float(os.getenv("AGENT_RETRY_BASE", "2.0"))
RETRY_JITTER = float(os.getenv("AGENT_RETRY_JITTER", "1.0"))

# 配置运行目录（run_state 会确保目录存在）
from deepagents.run_state import configure_runtime as _cfg_runtime
_cfg_runtime(
    run_dir=os.getenv("RUN_DIR", "./run_store"),
    mem_dir=os.getenv("MEMORY_DIR", "./mem_store"),
)

# ====== Helpers ======
def _sleep_backoff(i: int):
    delay = RETRY_BASE * (2**i) + random.uniform(0, RETRY_JITTER)
    time.sleep(delay)

def invoke_agent_with_retry(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """统一的调用入口：优先走 LangGraph；失败重试；最终兜底回显用户输入"""
    last_err = None
    for i in range(RETRY_ATTEMPTS):
        try:
            if LG_ENABLED and lg_app is not None:
                # LangGraph 路径
                state = lg_app.invoke({"messages": messages})
                txt = state.get("rewritten_text")
                if not txt:
                    # 兜底再调一次底层 agent
                    res = agent.invoke({"messages": messages})
                    txt = _pick_output(res)
                return {"rewritten_text": txt}
            else:
                # 直连路径
                return agent.invoke({"messages": messages})
        except Exception as e:
            last_err = e
            _sleep_backoff(i)

    # 全失败：回退为最后一条用户输入
    last_user = next(
        (m["content"] for m in reversed(messages) if m.get("role") == "user"), ""
    )
    return {"rewritten_text": last_user}

# ====== 路由（使用三角色轮转）======
@app.post("/generate")
async def generate_report(
    q: Question, 
    background_tasks: BackgroundTasks,  # 1. 注入 BackgroundTasks 依赖
    x_session_id: Optional[str] = Header(default=None)
):
    try:
        # 1) Entrance：会话 & 历史
        session_id = x_session_id or q.session_id or str(uuid.uuid4())
        last_n = int(os.getenv("MEMORY_LOAD_LAST_N", "8"))
        history = load_memory(session_id, last_n=last_n)

        # 2) 立即创建运行状态并返回trace_id
        run_state = create_run_state(session_id, q.user_input)
        trace_id = run_state["trace_id"]
        
        # 3) 在后台异步处理任务 (这是主要修改)
        # 不再需要自己定义 process_task，直接将要执行的函数和参数添加到后台任务
        background_tasks.add_task(
            run_textual_flow_wrapper,  # 使用一个新的包装函数
            trace_id=trace_id,
            session_id=session_id,
            user_input=q.user_input,
            history=history
        )
        
        # 4) 立即返回trace_id，让前端开始监听状态
        # 这个响应会立刻发送，不会等待 run_textual_flow_wrapper 执行完毕
        from fastapi.responses import JSONResponse
        return JSONResponse({
            "trace_id": trace_id,
            "session_id": session_id,
            "status": "started",
            "message": "任务已开始，正在处理中..."
        })
    except Exception as e:
        print(f"❌ Generate端点错误: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# 5. 创建一个新的包装函数来包含原来的逻辑
def run_textual_flow_wrapper(trace_id: str, session_id: str, user_input: str, history: list):
    """
    这个函数包含了所有需要在后台运行的阻塞逻辑。
    """
    try:
        # 更新内存状态为开始处理
        from deepagents.run_state import update_memory_state
        update_memory_state(trace_id, {
            "plan_rationale": "正在分析您的请求...",
            "todo": [{"step": "prepare", "status": "in_progress", "desc": "正在准备任务环境"}]
        })
        
        # 跑 Textual Flow
        result = run_textual_flow(
            user_input=user_input,
            session_id=session_id,
            history=history,
            pick_output=_pick_output,
            agent_invoke_with_retry=invoke_agent_with_retry,
            plan_max_loops=int(os.getenv("PLAN_MAX_LOOPS","3")),
            step_max_attempts=int(os.getenv("STEP_MAX_ATTEMPTS","2")),
            pass_threshold=float(os.getenv("VAL_PASS_THRESHOLD","0.75")),
            overall_replan_max=int(os.getenv("OVERALL_REPLAN_MAX","1")),
        )

        output = result.get("final_text","")

        # Memory：记录对话
        try:
            save_memory(session_id, "user", user_input)
            save_memory(session_id, "assistant", output)
            append_step(result["trace_id"], "persist_memory", "ok")
        except Exception as e:
            append_step(result["trace_id"], "persist_memory", "error", {"error": str(e)})

        # 更新最终结果到内存状态
        update_memory_state(trace_id, {
            "final_text": output,
            "done": result["done"],
            "plan_rationale": result.get("plan_rationale",""),
            "validation": {"ok": result["done"], "status": "completed" if result["done"] else "failed"}
        })
        
    except Exception as e:
        print(f"❌ 任务处理失败: {e}")
        # 更新错误状态
        from deepagents.run_state import update_memory_state
        update_memory_state(trace_id, {
            "error": str(e),
            "validation": {"ok": False, "status": "failed", "feedback": [str(e)]}
        })

@app.post("/debug")
async def debug_report(
    q: Question, x_session_id: Optional[str] = Header(default=None)
):
    """直接调底层 agent，返回 messages 视图（便于排查 tool_calls）"""
    session_id = x_session_id or q.session_id or str(uuid.uuid4())
    history = load_memory(session_id, last_n=int(os.getenv("MEMORY_LOAD_LAST_N", "8")))
    messages: List[Dict[str, str]] = []
    for h in history:
        messages.append(
            {"role": h.get("role") or "user", "content": h.get("content") or ""}
        )
    messages.append({"role": "user", "content": q.user_input})

    res = agent.invoke({"messages": messages})
    msgs = res.get("messages", [])

    def view(m):
        return {
            "type": m.__class__.__name__ if hasattr(m, "__class__") else str(type(m)),
            "content": getattr(m, "content", None)
            if hasattr(m, "content")
            else m.get("content", None),
            "kwargs": getattr(m, "additional_kwargs", {})
            if hasattr(m, "additional_kwargs")
            else m.get("additional_kwargs", {}),
        }

    return {"session_id": session_id, "messages": [view(m) for m in msgs]}

@app.post("/memory/clear")
async def clear_session_memory(session_id: Optional[str] = Header(default=None)):
    if not session_id:
        raise HTTPException(status_code=400, detail="Missing session_id in header")
    clear_memory(session_id)
    return {"ok": True, "session_id": session_id}

@app.get("/health")
def health_check():
    ok = True
    try:
        dirs = get_runtime_dirs()
        os.makedirs(dirs["run_dir"], exist_ok=True)
        os.makedirs(dirs["mem_dir"], exist_ok=True)
    except Exception:
        ok = False
    return {
        "status": "ok" if ok else "degraded",
        "memory_backend": "file",
        **get_runtime_dirs(),
    }

# 查询运行状态（trace）
@app.get("/state/{trace_id}")
def get_state(trace_id: str):
    try:
        return load_trace_state(trace_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="trace_id not found")

@app.get("/states")
def list_states(session_id: Optional[str] = Query(None)):
    return {"items": list_trace_states(session_id=session_id)}

# 导入中断管理器
from deepagents.interrupt_manager import get_interrupt_manager
interrupt_manager = get_interrupt_manager()

@app.post("/interrupt/{trace_id}")
async def interrupt_task(trace_id: str):
    """中断指定任务 - 改进版本"""
    try:
        # 立即打印中断日志
        print(f"🚫 用户请求中断任务: {trace_id}")
        
        # 使用中断管理器中断任务
        success = interrupt_manager.interrupt_task(trace_id)
        
        if success:
            # 记录中断状态到运行状态
            try:
                append_step(trace_id, "interrupt", "ok", {"interrupted_by": "user", "timestamp": time.time()})
                set_validation(trace_id, "interrupted", {"reason": "用户请求中断"})
            except Exception as e:
                print(f"⚠️ 记录中断状态失败: {e}")
            
            print(f"✅ 任务 {trace_id} 中断成功")
            
            return {
                "ok": True, 
                "trace_id": trace_id, 
                "message": "Task interrupted successfully",
                "timestamp": time.time()
            }
        else:
            print(f"⚠️ 任务 {trace_id} 不存在或已完成")
            return {
                "ok": False, 
                "trace_id": trace_id, 
                "message": "Task not found or already completed"
            }
            
    except Exception as e:
        print(f"❌ 中断任务失败: {e}")
        return {
            "ok": False, 
            "trace_id": trace_id, 
            "error": str(e)
        }

@app.get("/interrupt/check/{trace_id}")
async def check_interrupted(trace_id: str):
    """检查任务是否被中断"""
    task_status = interrupt_manager.get_task_status(trace_id)
    return {
        "trace_id": trace_id,
        "interrupted": interrupt_manager.is_interrupted(trace_id),
        "task_status": task_status
    }

@app.get("/interrupt/status")
async def get_interrupt_status():
    """获取中断状态信息"""
    return interrupt_manager.get_all_status()

# 新增：流式状态更新端点
from fastapi.responses import StreamingResponse
import asyncio

@app.get("/stream/state/{trace_id}")
async def stream_task_state(trace_id: str):
    """流式推送任务状态更新"""
    async def generate():
        last_state = None
        poll_count = 0
        max_polls = 6000  # 10分钟
        
        while poll_count < max_polls:
            try:
                # 获取当前状态
                current_state = load_trace_state(trace_id)
                
                # 检查状态是否有变化
                if current_state != last_state:
                    # 发送状态更新
                    yield f"data: {json.dumps(current_state, ensure_ascii=False)}\n\n"
                    last_state = current_state
                    
                    # 检查是否完成
                    is_completed = current_state.get("validation", {}).get("ok", False) or \
                        (current_state.get("todo") and all(item.get("status") == "completed" for item in current_state["todo"]))
                    
                    if is_completed:
                        yield f"data: {json.dumps({'status': 'completed'}, ensure_ascii=False)}\n\n"
                        break
                
                # 检查是否被中断
                if interrupt_manager.is_interrupted(trace_id):
                    yield f"data: {json.dumps({'status': 'interrupted'}, ensure_ascii=False)}\n\n"
                    break
                
                poll_count += 1
                await asyncio.sleep(0.1)  # 100ms间隔
                
            except FileNotFoundError:
                # 任务状态文件不存在，可能还在初始化
                await asyncio.sleep(0.1)
                poll_count += 1
            except Exception as e:
                print(f"流式状态更新错误: {e}")
                yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
                break
        
        # 发送结束信号
        yield f"data: {json.dumps({'status': 'timeout'}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

# 新增：快速状态检查端点
@app.get("/quick/state/{trace_id}")
async def quick_check_state(trace_id: str):
    """快速检查任务状态，不返回完整数据"""
    try:
        state = load_trace_state(trace_id)
        return {
            "trace_id": trace_id,
            "has_data": True,
            "validation_ok": state.get("validation", {}).get("ok", False),
            "steps_count": len(state.get("steps", [])),
            "todo_count": len(state.get("todo", [])),
            "is_interrupted": interrupt_manager.is_interrupted(trace_id)
        }
    except FileNotFoundError:
        return {
            "trace_id": trace_id,
            "has_data": False,
            "validation_ok": False,
            "steps_count": 0,
            "todo_count": 0,
            "is_interrupted": False
        }

if __name__ == "__main__":
    uvicorn.run(f"{__name__}:app", host="0.0.0.0", port=8002)
