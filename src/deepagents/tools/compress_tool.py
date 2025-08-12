# app/tools/contract_text_tool.py
from __future__ import annotations
from typing import Annotated

from langchain_core.tools import tool, InjectedToolCallId
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState

# 你已有的 SiliconFlow 客户端（同步）
# 需提供: _call_siliconflow_with_meta(prompt, text, model, return_meta: bool)
from deepagents.siliconflow_client import sf_client


def _llm_contract_text(text: str, model: str) -> str:
    """
    调用 LLM（SiliconFlow）对文本进行精简/压缩。
    返回字符串；若得到其他类型，尽量转成字符串。
    """
    content, _meta = sf_client._call_siliconflow_with_meta(
        sf_client._CONTRACT_TEXT_PROMPT,
        text,
        model,
        False,  # 与原路由一致：不需要额外 meta
    )
    if isinstance(content, str):
        return content
    try:
        import json
        return json.dumps(content, ensure_ascii=False)
    except Exception:
        return str(content)


TOOL_DESC = """精简一段文本（压缩表达、保留要点）。
参数：
- text: 原始文本
- model: 使用的模型名（如 deepseek_v3）
返回：
- 将精简结果写入 state['contracted_text']，并追加一条 ToolMessage。
"""

@tool(description=TOOL_DESC)
def contract_text_tool(
    text: str,
    model: str = "deepseek_v3",
    state: Annotated[dict, InjectedState] = None,
    tool_call_id: Annotated[str, InjectedToolCallId] = "",
) -> Command:
    """
    最小依赖版本：仅接收 text 与 model，返回 Command 更新 state。
    不做用户校验 / 不写数据库。
    """
    try:
        if not text or not text.strip():
            raise ValueError("请输入非空文本。")

        contracted = _llm_contract_text(text, model)

        return Command(
            update={
                "contracted_text": contracted,  # 单次结果：state['contracted_text']
                "messages": [
                    ToolMessage(
                        f"Text contracted successfully with model={model}.",
                        tool_call_id=tool_call_id,
                    )
                ],
            }
        )
    except Exception as e:
        return Command(
            update={
                "messages": [
                    ToolMessage(f"Failed to contract text: {e}", tool_call_id=tool_call_id)
                ]
            }
        )
