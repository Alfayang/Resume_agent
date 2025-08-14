from __future__ import annotations
import json, re, time, uuid, os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Callable

from deepagents.run_state import (
    create_run_state,
    append_step,
    set_todo_status,
    set_validation,
    validate_output,
)

# ============ 裸 LLM（供 Planner / Validator 使用，避免被 main agent 提示干扰） ============
from deepagents.model import get_default_model
_raw_llm = get_default_model()

def llm_invoke_json(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    res = _raw_llm.invoke(messages)
    content = getattr(res, "content", None) or str(res)
    return {"rewritten_text": content}

# ========================= 数据结构 =========================
@dataclass
class TodoStep:
    id: str
    title: str
    accept_criteria: List[str] = field(default_factory=list)
    need_validation: bool = True
    status: str = "pending"          # pending / in_progress / completed / failed
    attempts: int = 0
    max_attempts: int = 2
    outputs: Dict[str, Any] = field(default_factory=dict)
    tool_hint: Optional[str] = None  # 如：rewrite_text / expand_text / ...

@dataclass
class PlanResult:
    can_plan: bool
    rationale: str
    steps: List[TodoStep]

# 类型别名
PlannerFn   = Callable[[Dict[str, Any]], PlanResult]
ExecutorFn  = Callable[[Dict[str, Any], TodoStep], Dict[str, Any]]
ValidatorFn = Callable[[Dict[str, Any], TodoStep, List[TodoStep]], Tuple[bool, str]]

# ========================= 小工具 =========================
def _json_extract(text: str) -> str:
    if not isinstance(text, str):
        return ""
    stack, start = [], -1
    for i, ch in enumerate(text):
        if ch in "{[":
            if not stack: start = i
            stack.append(ch)
        elif ch in "}]":
            if not stack: continue
            left = stack.pop()
            if (left == "{" and ch != "}") or (left == "[" and ch != "]"):
                continue
            if not stack and start != -1:
                return text[start:i+1]
    m = re.search(r'(\{.*\}|\[.*\])', text, flags=re.S)
    return m.group(1) if m else ""

def _jloads(s: str, default):
    try:
        return json.loads(s)
    except Exception:
        return default

def _now():
    return time.strftime("%H:%M:%S")

def _log(trace_id: str, msg: str):
    append_step(trace_id, "log", "info", {"t": _now(), "msg": msg})

def _check_interruption(trace_id: str) -> bool:
    """检查任务是否被中断（改进版本）"""
    try:
        from deepagents.interrupt_manager import get_interrupt_manager
        interrupt_manager = get_interrupt_manager()
        is_interrupted = interrupt_manager.is_interrupted(trace_id)
        if is_interrupted:
            print(f"🛑 检测到中断信号: {trace_id}")
        return is_interrupted
    except ImportError:
        return False

def _steps_outline(steps: List[TodoStep]) -> List[Dict[str, Any]]:
    return [{"idx": i+1, "title": s.title, "need_validation": s.need_validation, "tool_hint": s.tool_hint} for i, s in enumerate(steps)]

# ========================= 路由表（标题/关键词 → 工具名） =========================
ROUTES = [
    (["解析简历","parse","简历"],       "parse_resume_text"),
    (["重写","rewrite","改写"],         "rewrite_text"),
    (["扩写","expand","丰富"],          "expand_text"),
    (["精简","压缩","contract"],        "contract_text"),
    (["评估","打分","evaluate"],        "evaluate_resume"),
    (["个人陈述","statement","SOP"],    "generate_statement"),
    (["推荐信","recommendation"],       "generate_recommendation"),
    (["命名","标题","name"],            "name_document"),
]
FINAL_TOOL_BY_ACTION = {
    "expand": "expand_text",
    "contract": "contract_text",
    "rewrite_letter": "rewrite_text",
    "generate_statement": "generate_statement",
    "generate_recommendation": "generate_recommendation",
    "name_document": "name_document",
    "parse_resume_text": "parse_resume_text",
}
FINAL_TOOLS = set(FINAL_TOOL_BY_ACTION.values())

ANALYSIS_KEYWORDS = ["分析","确定","设计","制定","规划","标准","流程","框架","方案","criterion","criteria","plan","design","spec","质量监控","验证标准"]
def is_analysis_step(title: str) -> bool:
    t = title.lower()
    return any(k.lower() in t for k in ANALYSIS_KEYWORDS)

def _guess_tool_by_title(title: str) -> Optional[str]:
    t = title.lower()
    for kws, tool in ROUTES:
        if any(k.lower() in t for k in kws):
            return tool
    return None

# ========================= Planner：产出子任务 + 可行性评估（≤N次） =========================
def make_llm_planner(max_loops: int = 3) -> PlannerFn:
    def _history_brief(msgs: List[Dict[str,str]], n: int = 6, max_chars: int = 800) -> str:
        parts = []
        for h in msgs[-n:]:
            role = h.get("role","user")
            content = (h.get("content") or "").strip().replace("\n"," ")[:200]
            parts.append(f"{role}: {content}")
        return "\n".join(parts)[:max_chars]

    def _ask_for_plan(ctx: Dict[str, Any], feedback: str = "") -> PlanResult:
        user_input = ctx.get("user_input","")
        action     = ctx.get("action","rewrite_letter")
        msgs       = ctx.get("messages", [])
        hist_txt   = _history_brief(msgs)

        sys = (
            "你是一名 Planner。请先分解用户任务为 2~8 个可执行子任务（steps），"
            "再做一次可行性评估（feasible=true/false，若 false 在 rationale 中说明阻碍与需要的信息）。"
            "每个子任务包含：title、accept_criteria[]、need_validation、tool_hint（可选）。"
            "严格只输出 JSON。"
        )
        usr = f"""
【任务类型】{action}
【用户输入】{user_input}
【近期历史】\n{hist_txt}
【上次反馈/阻碍】{feedback or "无"}

输出 JSON：
{{
  "feasible": true/false,
  "rationale": "可行/不可行的理由或信息缺口",
  "steps": [
    {{
      "title": "动词开头",
      "accept_criteria": ["可测标准1","标准2"],
      "need_validation": true,
      "tool_hint": "rewrite_text / expand_text / parse_resume_text / ..."
    }}
  ]
}}
"""
        res = llm_invoke_json([
            {"role":"system","content":sys},
            {"role":"user","content":usr}
        ])
        text = res.get("rewritten_text") or str(res)
        data = _jloads(_json_extract(text), {})
        feasible = bool(data.get("feasible", False))
        steps_raw = data.get("steps", [])
        steps: List[TodoStep] = []
        for s in steps_raw:
            title = s.get("title") or "执行主要动作"
            ac    = s.get("accept_criteria") or []
            if isinstance(ac, str): ac = [ac]
            nv    = bool(s.get("need_validation", True))
            hint  = s.get("tool_hint") or _guess_tool_by_title(title)
            steps.append(TodoStep(
                id=str(uuid.uuid4()),
                title=title,
                accept_criteria=ac,
                need_validation=nv,
                tool_hint=hint,
            ))

        # 分析类步骤默认不校验，避免被卡在“元任务”
        for st in steps:
            if is_analysis_step(st.title):
                st.need_validation = False

        # 保证最终至少有一个“能产出交付物”的步骤
        if not any((s.tool_hint in FINAL_TOOLS) for s in steps):
            tool = FINAL_TOOL_BY_ACTION.get(action, "rewrite_text")
            steps.append(TodoStep(
                id=str(uuid.uuid4()),
                title=f"生成最终结果（{action}）",
                accept_criteria=["满足用户目标","不得包含解释性文字","格式正确可直接交付"],
                need_validation=True,
                tool_hint=tool,
            ))

        rationale = data.get("rationale") or ""
        return PlanResult(can_plan=feasible and (2 <= len(steps) <= 8), rationale=rationale, steps=steps)

    def _planner(ctx: Dict[str, Any]) -> PlanResult:
        fb = ctx.get("last_failed_feedback","")
        for _ in range(max_loops):
            pr = _ask_for_plan(ctx, feedback=fb)
            if pr.can_plan:
                return pr
            fb = (pr.rationale or "信息不足").strip()

        # fallback：若有可处理文本，仍产一个最小三步以推进
        user_text = (ctx.get("user_input") or "").strip()
        if user_text:
            action = ctx.get("action","rewrite_letter")
            steps = [
                TodoStep(id=str(uuid.uuid4()), title=f"解析任务（{action}）",
                         accept_criteria=["明确目标与输出形式"], need_validation=False),
                TodoStep(id=str(uuid.uuid4()), title=f"执行主要动作（{action}）",
                         accept_criteria=["产物满足目标","不得包含解释性文字"], tool_hint=FINAL_TOOL_BY_ACTION.get(action,"rewrite_text")),
                TodoStep(id=str(uuid.uuid4()), title="收尾与格式检查",
                         accept_criteria=["格式正确","可直接交付"], need_validation=False),
            ]
            return PlanResult(can_plan=True, rationale=f"fallback: {fb or '信息不足'}", steps=steps)
        return PlanResult(can_plan=False, rationale=fb or "多次尝试仍无法规划", steps=[])
    return _planner

# ========================= Executor（按清单逐一执行） =========================
def make_executor(
    *,
    agent_invoke_with_retry: Callable[[List[Dict[str, str]]], Dict[str, Any]],
    pick_output: Callable[[Any], str],
) -> ExecutorFn:
    def _exec(ctx: Dict[str, Any], step: TodoStep) -> Dict[str, Any]:
        # 元步骤：直接返回分析信息
        if any(k in step.title for k in ["解析任务", "分析需求", "检查格式"]):
            return {"analysis": {"step": step.title, "preview": (ctx.get("user_input","")[:200])}}

        user_text = ctx.get("user_input", "")
        fix = (ctx.get("last_failed_feedback") or "").strip()

        if step.tool_hint:
            payload = {
                "action": step.tool_hint,
                "inputs": {"text": user_text, "letter": user_text},
                "model": "deepseek_v3"
            }
            if fix:
                payload["inputs"]["fix_guidance"] = fix
            sys_prompt = "你是 doc-writer 子代理的调度前端，只输出工具产物。"
            if fix:
                sys_prompt += f" 必须按以下修正点调整结果：{fix}"
            msgs = [
                {"role":"system","content": sys_prompt},
                {"role":"user","content": json.dumps(payload, ensure_ascii=False)}
            ]
            res = agent_invoke_with_retry(msgs)
            txt = pick_output(res)
            if isinstance(txt, (dict, list)):
                txt = json.dumps(txt, ensure_ascii=False, indent=2)
            return {"text": txt, "used_tool": step.tool_hint}

        # 无 hint：交给 main agent 自选工具，同时注入修正点
        msgs = list(ctx.get("messages", []))
        if fix:
            msgs.append({"role":"system","content": f"请严格依据以下必须修正点修改输出：{fix}。只输出最终结果，不要解释。"})
        res  = agent_invoke_with_retry(msgs)
        txt  = pick_output(res)
        if isinstance(txt, (dict, list)):
            txt = json.dumps(txt, ensure_ascii=False, indent=2)
        return {"text": txt}
    return _exec

# ========================= Validator（逐步验收；拿到“任务清单+该步结果”） =========================
def make_llm_validator(
    *, pass_threshold: float = 0.75
) -> ValidatorFn:
    def _validator(ctx: Dict[str, Any], step: TodoStep, all_steps: List[TodoStep]) -> Tuple[bool, str]:
        if not step.need_validation:
            return True, "无需校验"

        candidate = step.outputs.get("text") or step.outputs.get("final") or ""
        if not candidate and step.outputs:
            candidate = json.dumps(step.outputs, ensure_ascii=False)
        if not candidate:
            return False, "未产生可评审输出"

        sys = "你是严格的 Validator。仅输出 JSON。"
        usr = f"""
【当前子任务】{step.title}
【任务清单】{json.dumps(_steps_outline(all_steps), ensure_ascii=False)}
【验收标准】{json.dumps(step.accept_criteria, ensure_ascii=False)}
【候选输出】<<<BEGIN>>>
{candidate}
<<<END>>>

只输出：
{{
  "passed": true/false,
  "score": 0.0~1.0,
  "must_fix": ["若不通过，列出必须修改点（简短可执行）"],
  "feedback": "一句话结论"
}}
"""
        res  = llm_invoke_json([
            {"role":"system","content":sys},
            {"role":"user","content":usr}
        ])
        data = _jloads(_json_extract(res.get("rewritten_text") or str(res)), {})
        llm_pass  = bool(data.get("passed", False))
        llm_score = float(data.get("score", 0.0))
        fb        = data.get("feedback") or ""
        must_fix  = data.get("must_fix") or []

        # 规则硬校验（执行类严格）
        if any(k in step.title for k in ["执行","生成","重写","扩写","精简","推荐","陈述","命名","解析","评估"]) or (step.tool_hint in FINAL_TOOLS):
            action = ctx.get("action","rewrite_letter")
            ok_rule, issues = validate_output(action, candidate)
            if not ok_rule:
                fb = ("规则失败: " + "; ".join(issues or [])) + ((" | 必改: " + "; ".join(must_fix)) if must_fix else "")
                return False, fb

        passed = (llm_pass and llm_score >= pass_threshold)
        if not passed and must_fix:
            fb = fb + " | 必改: " + "; ".join(must_fix)
        return passed, fb or ("分数不足" if not passed else "OK")
    return _validator

# ========================= Planner 总体复评 & 可能的重规划 =========================
def planner_overall_review(
    ctx: Dict[str, Any],
    steps: List[TodoStep],
    outputs: Dict[str, Any],
) -> Tuple[bool, str, List[TodoStep]]:
    """
    返回：overall_ok, rationale, new_steps
    """
    sys = (
        "你是 Planner-Reviewer。你将收到：任务清单（含工具提示）、各步通过与产出，以及用户原始需求。"
        "请判断整体是否合理、是否达成用户目标。若不合理，请给出修订版子任务清单（2~8步）。"
        "严格只输出 JSON。"
    )
    outline = _steps_outline(steps)
    steps_report = []
    for i, st in enumerate(steps, 1):
        steps_report.append({
            "idx": i,
            "title": st.title,
            "status": st.status,
            "need_validation": st.need_validation,
            "tool_hint": st.tool_hint,
            "outputs_keys": list(st.outputs.keys()),
            "sample": (st.outputs.get("text") or "")[:200]
        })
    usr = f"""
【用户输入】{ctx.get("user_input","")}
【任务清单】{json.dumps(outline, ensure_ascii=False)}
【执行结果摘要】{json.dumps(steps_report, ensure_ascii=False)}

只输出：
{{
  "overall_ok": true/false,
  "rationale": "整体合理性判断依据；若为 false，指出关键缺口",
  "revised_steps": [
    {{
      "title": "动词开头",
      "accept_criteria": ["可测标准1","标准2"],
      "need_validation": true,
      "tool_hint": "可选"
    }}
  ]
}}
"""
    res = llm_invoke_json([
        {"role":"system","content":sys},
        {"role":"user","content":usr}
    ])
    data = _jloads(_json_extract(res.get("rewritten_text") or str(res)), {})
    overall_ok = bool(data.get("overall_ok", False))
    rationale  = data.get("rationale") or ""
    new_steps: List[TodoStep] = []
    for s in data.get("revised_steps", []) or []:
        title = s.get("title") or "执行主要动作"
        ac    = s.get("accept_criteria") or []
        if isinstance(ac, str): ac = [ac]
        nv    = bool(s.get("need_validation", True))
        hint  = s.get("tool_hint") or _guess_tool_by_title(title)
        ns = TodoStep(id=str(uuid.uuid4()), title=title, accept_criteria=ac, need_validation=nv, tool_hint=hint)
        if is_analysis_step(ns.title): ns.need_validation = False
        new_steps.append(ns)

    # 保证新清单也有最终产出
    if new_steps and not any((s.tool_hint in FINAL_TOOLS) for s in new_steps):
        tool = FINAL_TOOL_BY_ACTION.get(ctx.get("action","rewrite_letter"), "rewrite_text")
        new_steps.append(TodoStep(
            id=str(uuid.uuid4()),
            title=f"生成最终结果（{ctx.get('action','rewrite_letter')}）",
            accept_criteria=["满足用户目标","不得包含解释性文字","格式正确可直接交付"],
            need_validation=True,
            tool_hint=tool,
        ))
    return overall_ok, rationale, new_steps

# ========================= 主调度：按你的新流程 =========================
def run_textual_flow(
    *,
    user_input: str,
    session_id: Optional[str],
    history: List[Dict[str, str]],
    pick_output: Callable[[Any], str],
    agent_invoke_with_retry: Callable[[List[Dict[str, str]]], Dict[str, Any]],
    plan_max_loops: int = 3,
    step_max_attempts: int = 2,
    pass_threshold: float = 0.75,
    overall_replan_max: Optional[int] = None,   # None→从环境变量读取
) -> Dict[str, Any]:
    """
    流程：
    1) Planner 分解 + 可行性评估（≤ plan_max_loops）
    2) 把 steps 交给 Executor 逐一执行；每步后用 Validator 校验（把任务清单 + 该步输出给 Validator）
       - 若不合理 → 给出 must_fix，Executor 依据建议重试（≤ step_max_attempts）
       - 达上限仍不过 → 记为 failed，继续后续步（不在此处重规划）
    3) 全部执行后 → 把整体结果给 Planner 做总体复评
       - 若不合理 → 修订子任务清单并重跑执行（≤ overall_replan_max 次）
    4) 返回最终结果
    """
    if overall_replan_max is None:
        overall_replan_max = int(os.getenv("OVERALL_REPLAN_MAX", "1"))

    # 入口与上下文
    run_state = create_run_state(session_id, user_input)
    trace_id  = run_state["trace_id"]
    action    = run_state.get("action_guess", "rewrite_letter")

    ctx: Dict[str, Any] = {
        "session_id": session_id,
        "trace_id": trace_id,
        "action": action,
        "user_input": user_input,
        "messages": [{"role": h.get("role","user"), "content": h.get("content","")} for h in history] + [
            {"role":"user","content": user_input}
        ],
        "last_failed_feedback": ""
    }
    _log(trace_id, "Initial Prompt received")
    
    # 注册任务到中断管理器
    try:
        from deepagents.interrupt_manager import get_interrupt_manager
        interrupt_manager = get_interrupt_manager()
        interrupt_manager.register_task(trace_id, user_input)
        print(f"🚀 开始处理任务: {trace_id}")
    except ImportError:
        pass

    # 1) 规划 + 可行性评估
    planner = make_llm_planner(max_loops=plan_max_loops)
    set_todo_status(trace_id, "plan", "in_progress")
    append_step(trace_id, "planner", "started", {"action": action})

    pr = planner(ctx)
    if not pr.can_plan:
        set_todo_status(trace_id, "plan", "failed")
        append_step(trace_id, "planner", "failed", {"reason": pr.rationale})
        return {
            "trace_id": trace_id,
            "session_id": session_id,
            "done": False,
            "plan_rationale": pr.rationale,
            "checklist": [],
            "final_text": "",
        }

    steps = pr.steps
    for s in steps:
        s.max_attempts = step_max_attempts

    set_todo_status(trace_id, "plan", "completed")
    append_step(trace_id, "planner", "ok", {"steps": [s.title for s in steps], "rationale": pr.rationale})

    executor  = make_executor(agent_invoke_with_retry=agent_invoke_with_retry, pick_output=pick_output)
    validator = make_llm_validator(pass_threshold=pass_threshold)

    def _execute_all(current_steps: List[TodoStep]) -> Tuple[List[TodoStep], str]:
        final_text = ""
        for idx, step in enumerate(current_steps):
            # 执行（带重试 + must_fix）
            while True:
                # 检查是否被中断 - 在每个步骤开始时检查
                if _check_interruption(trace_id):
                    append_step(trace_id, "executor", "interrupted", {"step": step.title, "reason": "User requested interruption"})
                    set_todo_status(trace_id, f"step-{idx+1}", "interrupted")
                    
                    # 清理任务
                    try:
                        from deepagents.interrupt_manager import get_interrupt_manager
                        interrupt_manager = get_interrupt_manager()
                        interrupt_manager.cleanup_task(trace_id)
                        print(f"🛑 执行步骤被中断，清理任务信息: {trace_id}")
                    except ImportError:
                        pass
                    
                    return current_steps, final_text
                
                set_todo_status(trace_id, f"step-{idx+1}", "in_progress")
                append_step(trace_id, "executor", "started", {"step": step.title, "attempt": step.attempts+1})
                step.status   = "in_progress"
                step.attempts += 1
                
                # 在每次重试前也检查中断状态
                if _check_interruption(trace_id):
                    append_step(trace_id, "executor", "interrupted", {"step": step.title, "reason": "User requested interruption during retry"})
                    set_todo_status(trace_id, f"step-{idx+1}", "interrupted")
                    
                    # 清理任务
                    try:
                        from deepagents.interrupt_manager import get_interrupt_manager
                        interrupt_manager = get_interrupt_manager()
                        interrupt_manager.cleanup_task(trace_id)
                        print(f"🛑 重试步骤被中断，清理任务信息: {trace_id}")
                    except ImportError:
                        pass
                    
                    return current_steps, final_text
                try:
                    out = executor(ctx, step) or {}
                    step.outputs.update(out)
                    append_step(trace_id, "executor", "ok", {"outputs_keys": list(out.keys()), "tool": out.get("used_tool")})
                except Exception as e:
                    append_step(trace_id, "executor", "error", {"error": repr(e)})
                    if step.attempts < step.max_attempts:
                        step.status = "pending"
                        set_todo_status(trace_id, f"step-{idx+1}", "pending")
                        continue
                    step.status = "failed"
                    set_todo_status(trace_id, f"step-{idx+1}", "failed")
                    break  # 放弃该步，继续后续

                # 校验
                if step.need_validation:
                    set_todo_status(trace_id, f"step-{idx+1}-validate", "in_progress")
                    passed, fb = validator(ctx, step, current_steps)
                    append_step(trace_id, "validator", "ok" if passed else "warn", {"step": step.title, "feedback": fb})
                    set_validation(trace_id, passed, [fb] if fb else [])
                    if not passed:
                        if step.attempts < step.max_attempts:
                            step.status = "pending"
                            set_todo_status(trace_id, f"step-{idx+1}-validate", "pending")
                            ctx["last_failed_feedback"] = fb
                            continue  # 再试同一步
                        else:
                            step.status = "failed"
                            set_todo_status(trace_id, f"step-{idx+1}", "failed")
                            break

                # 通过
                step.status = "completed"
                set_todo_status(trace_id, f"step-{idx+1}", "completed")
                set_todo_status(trace_id, f"step-{idx+1}-validate", "completed")
                if "text" in step.outputs:  final_text = step.outputs["text"]
                if "final" in step.outputs: final_text = step.outputs["final"]
                break
        return current_steps, final_text

    # 2) 执行清单（第一次）
    steps, final_text = _execute_all(steps)

    # 3) Planner 总体复评（可重规划≤overall_replan_max）
    replan_times = 0
    while True:
        # 检查是否被中断
        if _check_interruption(trace_id):
            append_step(trace_id, "planner_review", "interrupted", {"reason": "User requested interruption during overall review"})
            
            # 清理任务
            try:
                from deepagents.interrupt_manager import get_interrupt_manager
                interrupt_manager = get_interrupt_manager()
                interrupt_manager.cleanup_task(trace_id)
                print(f"🛑 任务被中断，清理任务信息: {trace_id}")
            except ImportError:
                pass
            
            return {
                "trace_id": trace_id,
                "session_id": session_id,
                "done": False,
                "plan_rationale": "Task interrupted by user",
                "checklist": [s.__dict__ for s in steps],
                "final_text": final_text,
            }
        
        overall_ok, rationale, new_steps = planner_overall_review(ctx, steps, {"final_text": final_text})
        append_step(trace_id, "planner_review", "ok" if overall_ok else "warn", {"rationale": rationale})

        if overall_ok or replan_times >= overall_replan_max or not new_steps:
            done = overall_ok and all(s.status == "completed" or not s.need_validation for s in steps)
            
            # 清理任务
            try:
                from deepagents.interrupt_manager import get_interrupt_manager
                interrupt_manager = get_interrupt_manager()
                interrupt_manager.cleanup_task(trace_id)
                print(f"✅ 任务完成，清理任务信息: {trace_id}")
            except ImportError:
                pass
            
            return {
                "trace_id": trace_id,
                "session_id": session_id,
                "done": done,
                "plan_rationale": pr.rationale if overall_ok else f"overall_review: {rationale}",
                "checklist": [s.__dict__ for s in steps],
                "final_text": final_text,
            }

        # 触发重规划：用新清单重跑
        replan_times += 1
        append_step(trace_id, "planner", "replan", {"times": replan_times, "new_steps": [s.title for s in new_steps]})
        for s in new_steps:
            s.max_attempts = step_max_attempts
        # 重置失败反馈，执行新清单
        ctx["last_failed_feedback"] = ""
        # 重跑
        steps, final_text = _execute_all(new_steps)
