# research_agent.py

# 在文件顶部从 fastapi 导入 BackgroundTasks
from fastapi import FastAPI, Header, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
import asyncio

# ... (其他导入)

# ====== 路由（使用三角色轮转）======
@app.post("/generate")
async def generate_report(
    q: Question, 
    background_tasks: BackgroundTasks,  # 1. 注入 BackgroundTasks 依赖
    x_session_id: Optional[str] = Header(default=None)
):
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
    return JSONResponse({
        "trace_id": trace_id,
        "session_id": session_id,
        "status": "started",
        "message": "任务已开始，正在处理中..."
    })

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

# ... (其他代码保持不变)