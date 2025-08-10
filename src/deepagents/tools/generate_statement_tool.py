# app/tools/generate_statement_tool.py
from __future__ import annotations
import json
from typing import Annotated, Dict, Any

from langchain_core.tools import tool, InjectedToolCallId
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState

# 你已有的 SiliconFlow 客户端（同步）
# 需提供: _call_siliconflow_with_meta(prompt, text, model, return_meta: bool)
from deepagents.siliconflow_client import sf_client


def _llm_generate_statement(text: str, model: str) -> Dict[str, Any]:
    """
    调用 LLM 生成个人陈述。
    统一返回 dict；若为字符串则尝试 json 解析，失败则包一层。
    """
    content, _meta = sf_client._call_siliconflow_with_meta(
        sf_client._GENERATE_STATEMENT_PROMPT,
        text,
        model,
        True,  # 与原路由一致：需要 meta（虽不返回，但保留兼容）
    )

    # content 可能是 dict 或 str
    if isinstance(content, dict):
        return content
    try:
        return json.loads(content)
    except Exception:
        return {"statement": str(content)}

TOOL_DESC = """根据输入信息生成一份个人陈述（Personal Statement）。
参数：
- text: 与个人陈述相关的信息（背景、经历、亮点、目标等）
- model: 使用的模型名（如 deepseek_v3）
返回：
- 将生成结果写入 state['generated_statement']，并追加一条 ToolMessage。
"""

@tool(description=TOOL_DESC)
def generate_statement_tool(
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
            raise ValueError("请输入非空的个人信息文本。")

        statement = _llm_generate_statement(text, model)

        # 如果上游以 {"error": "..."} 形式返回，抛出给上层处理
        if isinstance(statement, dict) and "error" in statement:
            raise RuntimeError(statement.get("error"))

        return Command(
            update={
                "generated_statement": statement,  # 写入到 state
                "messages": [
                    ToolMessage(
                        f"Personal statement generated with model={model}.",
                        tool_call_id=tool_call_id,
                    )
                ],
            }
        )
    except Exception as e:
        return Command(
            update={
                "messages": [
                    ToolMessage(f"Failed to generate personal statement: {e}", tool_call_id=tool_call_id)
                ]
            }
        )
