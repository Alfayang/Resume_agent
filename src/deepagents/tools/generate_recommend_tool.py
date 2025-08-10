# app/tools/generate_recommendation_tool.py
from __future__ import annotations
import json
from typing import Annotated, Dict, Any

from langchain_core.tools import tool, InjectedToolCallId
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState

# 你的 SiliconFlow 客户端（同步调用）
# 需提供: _call_siliconflow_with_meta(prompt, text, model, return_meta: bool)
from deepagents.siliconflow_client import sf_client


def _llm_generate_recommendation(text: str, model: str) -> Dict[str, Any]:
    """
    调用 LLM 生成推荐信。
    返回 dict；若返回字符串，则尝试解析为 JSON，失败则包一层。
    """
    content, _meta = sf_client._call_siliconflow_with_meta(
        sf_client._GENERATE_RECOMMENDATION_PROMPT,
        text,
        model,
        True,  # 与原路由一致：保留 meta（虽然这里只用 content）
    )

    if isinstance(content, dict):
        return content
    try:
        return json.loads(content)
    except Exception:
        return {"recommendation": str(content)}


TOOL_DESC = """根据输入信息生成一封推荐信（JSON 格式）。
参数：
- text: 与推荐信相关的信息（背景、成就、关系等）
- model: 使用的模型名（如 deepseek_v3）
返回：
- 将生成的推荐信写入 state['generated_recommendation']，并追加一条 ToolMessage。
"""

@tool(description=TOOL_DESC)
def generate_recommendation_tool(
    text: str,
    model: str = "deepseek_v3",
    state: Annotated[Dict, InjectedState] = None,
    tool_call_id: Annotated[str, InjectedToolCallId] = "",
) -> Command:
    """
    最小依赖版本：仅接收 text 与 model，返回推荐信 JSON。
    不做用户校验 / 不写数据库。
    """
    try:
        if not text or not text.strip():
            raise ValueError("请输入非空的推荐信信息文本。")

        recommendation = _llm_generate_recommendation(text, model)

        if isinstance(recommendation, dict) and "error" in recommendation:
            raise RuntimeError(recommendation.get("error"))

        return Command(
            update={
                "generated_recommendation": recommendation,
                "messages": [
                    ToolMessage(
                        f"Recommendation letter generated with model={model}.",
                        tool_call_id=tool_call_id,
                    )
                ],
            }
        )
    except Exception as e:
        return Command(
            update={
                "messages": [
                    ToolMessage(f"Failed to generate recommendation letter: {e}", tool_call_id=tool_call_id)
                ]
            }
        )
