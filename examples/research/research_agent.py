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

from fastapi import FastAPI, Header, HTTPException, Query
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
RETRY_ATTEMPTS = int(os.getenv("AGENT_RETRY_ATTEMPTS", "3"))
RETRY_BASE = float(os.getenv("AGENT_RETRY_BASE", "0.6"))
RETRY_JITTER = float(os.getenv("AGENT_RETRY_JITTER", "0.3"))

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
    q: Question, x_session_id: Optional[str] = Header(default=None)
):
    # 1) Entrance：会话 & 历史
    session_id = x_session_id or q.session_id or str(uuid.uuid4())
    last_n = int(os.getenv("MEMORY_LOAD_LAST_N", "8"))
    history = load_memory(session_id, last_n=last_n)

    # 2) 跑 Textual Flow：Planner → (Loop) → Executor（逐个）→ Validator（逐个）→ Planner 总体复评（可重跑）
    result = run_textual_flow(
        user_input=q.user_input,
        session_id=session_id,
        history=history,
        pick_output=_pick_output,
        agent_invoke_with_retry=invoke_agent_with_retry,
        plan_max_loops=int(os.getenv("PLAN_MAX_LOOPS","3")),
        step_max_attempts=int(os.getenv("STEP_MAX_ATTEMPTS","2")),
        pass_threshold=float(os.getenv("VAL_PASS_THRESHOLD","0.75")),
        # ☆ 新增：总体复评的重规划上限（不填则在调度器内部按 env 读取）
        overall_replan_max=int(os.getenv("OVERALL_REPLAN_MAX","1")),
    )

    output = result.get("final_text","")

    # 3) Memory：记录对话
    try:
        save_memory(session_id, "user", q.user_input)
        save_memory(session_id, "assistant", output)
        append_step(result["trace_id"], "persist_memory", "ok")
    except Exception as e:
        append_step(result["trace_id"], "persist_memory", "error", {"error": str(e)})

    # 4) 返回（可在 /state/{trace_id} 查看完整 ToDo/步骤状态）
    return {
        "trace_id": result["trace_id"],
        "session_id": session_id,
        "rewritten_letter": output,
        "done": result["done"],
        "plan_rationale": result.get("plan_rationale",""),
        "steps": result.get("checklist", []),
    }

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

if __name__ == "__main__":
    uvicorn.run(f"{__name__}:app", host="0.0.0.0", port=8002)
