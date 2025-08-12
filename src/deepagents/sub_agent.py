# src/deepagents/sub_agent.py
from __future__ import annotations
from typing import TypedDict, NotRequired, Annotated, Any, Dict
import json

from langgraph.prebuilt import create_react_agent, InjectedState
from langgraph.types import Command
from langchain_core.tools import BaseTool, tool, InjectedToolCallId
from langchain_core.messages import ToolMessage

from deepagents.prompts import TASK_DESCRIPTION_PREFIX, TASK_DESCRIPTION_SUFFIX
from deepagents.state import DeepAgentState

class SubAgent(TypedDict):
    name: str
    description: str
    prompt: str
    tools: NotRequired[list[str]]  # 工具名字符串，需与 @tool(name="...") 一致

def _create_task_tool(tools, instructions, subagents: list[SubAgent], model, state_schema):
    """
    生成一个名为 `task` 的工具：
    - 接受 description(可为 dict/list/str) + subagent_type
    - 将任务路由给目标子代理
    - 合并子代理返回的 state（除 messages 外）
    - 回传一条 ToolMessage 作为汇报
    """

    # 1) 可选的“通用子代理”：不给任何工具，避免乱调（如不需要可删除此项）
    agents = {
        "general-purpose": create_react_agent(
            model, prompt=instructions, tools=[], state_schema=state_schema
        )
    }

    # 2) 建立 工具名 -> 工具对象 的映射
    tools_by_name = {}
    for tool_ in tools:
        if not isinstance(tool_, BaseTool):
            # 容错：如果传入的是函数，包装成 BaseTool
            from langchain_core.tools import tool as _wrap
            tool_ = _wrap(tool_)
        tools_by_name[tool_.name] = tool_

    # 3) 注册子代理，并按工具名字符串筛选工具
    for _agent in subagents:
        if "tools" in _agent:
            _tools = [tools_by_name[t] for t in _agent["tools"] if t in tools_by_name]
        else:
            _tools = []  # 不声明则不给工具，确保一切可控
        agents[_agent["name"]] = create_react_agent(
            model, prompt=_agent["prompt"], tools=_tools, state_schema=state_schema
        )

    # 4) 生成描述字符串展示有哪些子代理
    other_agents_lines = [f"- {_agent['name']}: {_agent['description']}" for _agent in subagents]
    other_agents_str = "\n".join(other_agents_lines) if other_agents_lines else "- (no extra subagents)"

    @tool(description=TASK_DESCRIPTION_PREFIX.format(other_agents=other_agents_str) + TASK_DESCRIPTION_SUFFIX)
    def task(
        description: Any,
        subagent_type: str,
        state: Annotated[DeepAgentState, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        # 5) 选择子代理
        if subagent_type not in agents:
            allowed = ", ".join(f"`{k}`" for k in agents.keys())
            return Command(update={"messages": [ToolMessage(
                f"Error: invoked agent type `{subagent_type}` not found. Allowed: {allowed}",
                tool_call_id=tool_call_id
            )]})

        sub_agent = agents[subagent_type]

        # 6) description 允许运行时传 dict/list，转 JSON 字符串
        if isinstance(description, (dict, list)):
            try:
                description = json.dumps(description, ensure_ascii=False)
            except Exception:
                description = str(description)

        # 7) 以 description 作为用户消息调用子代理（不带入历史，避免污染）
        new_state = dict(state)
        new_state["messages"] = [{"role": "user", "content": description}]
        try:
            result: Dict[str, Any] = sub_agent.invoke(new_state)
        except Exception as e:
            return Command(update={"messages": [ToolMessage(
                f"Subagent `{subagent_type}` failed: {e}", tool_call_id=tool_call_id
            )]})

        # 8) 合并子代理返回（除 messages）
        update: Dict[str, Any] = {}
        for k, v in result.items():
            if k != "messages":
                update[k] = v

        # 9) 取子代理最后一条消息作为汇报
        try:
            last_msg = result["messages"][-1].content
        except Exception:
            last_msg = "[Subagent finished with no final message]"

        update.setdefault("messages", [])
        update["messages"].append(ToolMessage(last_msg, tool_call_id=tool_call_id))
        return Command(update=update)

    return task
