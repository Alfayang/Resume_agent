# app/tools/parse_resume_text_tool.py
from __future__ import annotations
import json
from typing import Annotated, Dict, Any

from langchain_core.tools import tool, InjectedToolCallId
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState

# 你已有的 SiliconFlow 客户端（同步调用）
# 需要提供 _call_siliconflow_with_meta(prompt, text, model, return_meta=True)
from deepagents.siliconflow_client import sf_client


def _llm_parse_resume_from_text(text: str, model: str) -> Dict[str, Any]:
    """
    调用 LLM（SiliconFlow）解析简历文本，统一返回 dict。
    """
    content, meta = sf_client._call_siliconflow_with_meta(
        sf_client._PARSE_RESUME_PROMPT,
        text,
        model,
        True,  # return_meta
    )

    # content 可能是 dict 或 str，这里统一成 dict
    if isinstance(content, dict):
        return content
    try:
        return json.loads(content)
    except Exception:
        # 无法解析为JSON时，直接包一层
        return {"result": content, "meta": meta}


TOOL_DESC = """解析一段简历文本并返回结构化JSON。
参数：
- text: 简历纯文本
- model: 使用的解析模型名（如 deepseek_v3）
返回：
- 将解析结果写入 state['resume_parse']，并追加一条 ToolMessage。
"""

@tool(description=TOOL_DESC)
def parse_resume_text_tool(
    text: str,
    model: str = "deepseek_v3",
    state: Annotated[dict, InjectedState] = None,
    tool_call_id: Annotated[str, InjectedToolCallId] = "",
) -> Command:
    """
    最小依赖：仅接收文本和模型名，返回解析 JSON（写入 state）。
    不做用户校验、数据库写入。
    """
    try:
        if not text or not text.strip():
            raise ValueError("请输入非空的简历文本。")

        result = _llm_parse_resume_from_text(text, model)

        return Command(
            update={
                "resume_parse": result,  # 单一结果写入该键；如需累积可改为列表
                "messages": [
                    ToolMessage(
                        f"Resume text parsed successfully with model={model}.",
                        tool_call_id=tool_call_id,
                    )
                ],
            }
        )
    except Exception as e:
        return Command(
            update={
                "messages": [
                    ToolMessage(f"Failed to parse resume text: {e}", tool_call_id=tool_call_id)
                ]
            }
        )