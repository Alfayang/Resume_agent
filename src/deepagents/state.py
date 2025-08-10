from langgraph.prebuilt.chat_agent_executor import AgentState
from typing import Any, Dict, List, Optional
from typing import Annotated
from typing_extensions import TypedDict, NotRequired
from typing import Literal

class Todo(TypedDict):
    content: str
    status: Literal["pending", "in_progress", "completed"]

# --- reducers ---
def file_reducer(l: Optional[Dict[str, str]], r: Optional[Dict[str, str]]):
    if l is None: return r
    if r is None: return l
    return {**l, **r}  # 右侧覆盖左侧

def last_write(l, r):
    # 后写优先；None 不覆盖已有值
    return r if r is not None else l

def list_extend(l: Optional[List[Any]], r: Optional[List[Any]]):
    if l is None: return r
    if r is None: return l
    return [*l, *r]

class DeepAgentState(AgentState):
    # 内置
    todos: NotRequired[List[Todo]]
    files: Annotated[NotRequired[Dict[str, str]], file_reducer]

    # —— 我们的工具会写入的键（单结果：后写覆盖）——
    rewritten_text: Annotated[NotRequired[str], last_write]
    expanded_text: Annotated[NotRequired[str], last_write]
    contracted_text: Annotated[NotRequired[str], last_write]
    document_name: Annotated[NotRequired[str], last_write]

    resume_parse: Annotated[NotRequired[Dict[str, Any]], last_write]
    resume_evaluation: Annotated[NotRequired[str], last_write]

    generated_statement: Annotated[NotRequired[Dict[str, Any]], last_write]  # 或 str，看你的实现
    generated_recommendation: Annotated[NotRequired[Dict[str, Any]], last_write]

    # —— 如果你想累计历史结果，可保留这些列表（可选）——
    rewritten_texts: Annotated[NotRequired[List[str]], list_extend]
    expanded_texts: Annotated[NotRequired[List[str]], list_extend]
    contracted_texts: Annotated[NotRequired[List[str]], list_extend]
    resume_parses: Annotated[NotRequired[List[Dict[str, Any]]], list_extend]
