# src/deepagents/state.py
from typing import Any, Dict, List, Optional
from typing import Annotated
from typing_extensions import TypedDict, NotRequired
from typing import Literal
from langgraph.prebuilt.chat_agent_executor import AgentState

class Todo(TypedDict):
    content: str
    status: Literal["pending", "in_progress", "completed"]

# --- reducers ---
def file_reducer(l: Optional[Dict[str, str]], r: Optional[Dict[str, str]]):
    """合并字典：右侧覆盖左侧"""
    if l is None: return r
    if r is None: return l
    return {**l, **r}

def last_write(l, r):
    """后写优先；None 不覆盖已有值"""
    return r if r is not None else l

def list_extend(l: Optional[List[Any]], r: Optional[List[Any]]):
    """列表累加"""
    if l is None: return r
    if r is None: return l
    return [*l, *r]

class DeepAgentState(AgentState):
    """
    运行态 schema（在 LangGraph 节点之间传递）。
    你可以按需增删字段；Reducers 定义了并发/顺序写入时的合并策略。
    """

    # 内置可选：运行过程的待办
    todos: NotRequired[List[Todo]]

    # 产出文件（文件名 -> 路径）
    files: Annotated[NotRequired[Dict[str, str]], file_reducer]

    # —— 工具产出的“最新单值”（后写覆盖）——
    rewritten_text: Annotated[NotRequired[str], last_write]
    expanded_text: Annotated[NotRequired[str], last_write]
    contracted_text: Annotated[NotRequired[str], last_write]
    document_name: Annotated[NotRequired[str], last_write]

    resume_parse: Annotated[NotRequired[Dict[str, Any]], last_write]
    resume_evaluation: Annotated[NotRequired[str], last_write]

    generated_statement: Annotated[NotRequired[Dict[str, Any]], last_write]  # 或 str
    generated_recommendation: Annotated[NotRequired[Dict[str, Any]], last_write]

    # —— 保留多版本历史（可选）——
    rewritten_texts: Annotated[NotRequired[List[str]], list_extend]
    expanded_texts: Annotated[NotRequired[List[str]], list_extend]
    contracted_texts: Annotated[NotRequired[List[str]], list_extend]
    resume_parses: Annotated[NotRequired[List[Dict[str, Any]]], list_extend]

__all__ = [
    "Todo",
    "DeepAgentState",
    "file_reducer",
    "last_write",
    "list_extend",
]
