# src/deepagents/agent_factory.py
from __future__ import annotations
from typing import Sequence, Union, Callable, Any, Optional, TypeVar, Type
from langchain_core.tools import BaseTool
from langchain_core.language_models import LanguageModelLike
from langgraph.prebuilt import create_react_agent

from deepagents.sub_agent import _create_task_tool, SubAgent
from deepagents.state import DeepAgentState
from deepagents.model import get_default_model

StateSchema = TypeVar("StateSchema", bound=DeepAgentState)
StateSchemaType = Type[StateSchema]

# 如需基础提示可放在这里；不需要可留空
base_prompt = ""

def create_deep_agent(
    tools: Sequence[Union[BaseTool, Callable, dict[str, Any]]],
    instructions: str,
    model: Optional[Union[str, LanguageModelLike]] = None,
    subagents: list[SubAgent] | None = None,
    state_schema: Optional[StateSchemaType] = None,
    *,
    expose_tools_to_main: bool = False,  # ⭐ 关键：默认不把工具暴露给主 Agent
):
    """
    创建 Deep Agent（主 Agent 只暴露 task）。
    - tools: 供子代理使用的工具集合（主 Agent 默认看不到）
    - instructions: 主 Agent 系统提示，会与 base_prompt 拼接
    - subagents: 子代理配置（每个子代理声明可以使用哪些工具名）
    - expose_tools_to_main: 若 True，则主 Agent 也能直接看到这些 tools（一般保持 False）
    """
    prompt = (instructions + base_prompt) if base_prompt else instructions
    model = model or get_default_model()
    state_schema = state_schema or DeepAgentState

    # 只把工具交给 _create_task_tool（内部再分配给子代理）；主 Agent 不直接接触这些工具
    task_tool = _create_task_tool(
        list(tools),
        instructions,
        subagents or [],
        model,
        state_schema,
    )

    # 主 Agent 工具：默认只有 task；如确需暴露工具再设 True
    all_tools = [task_tool] if not expose_tools_to_main else list(tools) + [task_tool]

    return create_react_agent(
        model,
        prompt=prompt,
        tools=all_tools,
        state_schema=state_schema,
    )
