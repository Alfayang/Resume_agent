# app/tools/name_document_tool.py
from __future__ import annotations
from typing import Annotated

from langchain_core.tools import tool, InjectedToolCallId
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState

# 你的 SiliconFlow 客户端（同步调用）
# 需提供: _call_siliconflow_with_meta(prompt, text, model, return_meta: bool)
from deepagents.siliconflow_client import sf_client


def _llm_name_document(markdown_text: str, model: str) -> str:
    """
    调用 LLM 为 Markdown 文档生成标题。
    返回字符串；若得到其他类型，尽量转成字符串。
    """
    content, _meta = sf_client._call_siliconflow_with_meta(
        sf_client._NAME_DOCUMENT_PROMPT,
        markdown_text,
        model,
        False,  # 与原路由一致：无需额外 meta
    )
    if isinstance(content, str):
        return content
    try:
        import json
        return json.dumps(content, ensure_ascii=False)
    except Exception:
        return str(content)


TOOL_DESC = """为一段 Markdown 文档生成合适的标题。
参数：
- text: Markdown 文本内容
- model: 使用的模型名（如 deepseek_v3）
返回：
- 将标题写入 state['document_name']，并追加一条 ToolMessage。
"""

@tool(description=TOOL_DESC)
def name_document_tool(
    text: str,
    model: str = "deepseek_v3",
    state: Annotated[dict, InjectedState] = None,
    tool_call_id: Annotated[str, InjectedToolCallId] = "",
) -> Command:
    """
    最小依赖版本：仅接收 text 与 model。
    不做用户校验 / 不写数据库。
    """
    try:
        if not text or not text.strip():
            raise ValueError("请输入非空的 Markdown 文本。")

        title = _llm_name_document(text, model)

        return Command(
            update={
                "document_name": title,
                "messages": [
                    ToolMessage(
                        f"Document title generated with model={model}.",
                        tool_call_id=tool_call_id,
                    )
                ],
            }
        )
    except Exception as e:
        return Command(
            update={
                "messages": [
                    ToolMessage(f"Failed to generate document title: {e}", tool_call_id=tool_call_id)
                ]
            }
        )
