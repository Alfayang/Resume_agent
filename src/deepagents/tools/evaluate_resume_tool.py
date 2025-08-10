# app/tools/evaluate_resume_tool.py
from __future__ import annotations
import json
from typing import Annotated, Any, Dict

from langchain_core.tools import tool, InjectedToolCallId
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState

# 你的 SiliconFlow 客户端（同步调用）
# 需提供: _call_siliconflow_with_meta(prompt, text, model, return_meta: bool)
from deepagents.siliconflow_client import sf_client


def _serialize_data_to_text(data: Any) -> str:
    """将 dict/list/str 等输入转为给 LLM 的字符串。"""
    if isinstance(data, (dict, list)):
        return json.dumps(data, indent=2, ensure_ascii=False)
    if isinstance(data, str):
        # 若传入本身是字符串，尽量规范化（可选）
        try:
            parsed = json.loads(data)
            return json.dumps(parsed, indent=2, ensure_ascii=False)
        except Exception:
            return data
    # 其它类型也尝试转 JSON；失败则转字符串
    try:
        return json.dumps(data, ensure_ascii=False)
    except Exception:
        return str(data)


def _llm_evaluate_resume(json_like_text: str, model: str) -> str:
    """
    调用 LLM（SiliconFlow）对简历数据进行评价/分析。
    返回字符串；若得到其他类型，尽量转成字符串。
    """
    content, _meta = sf_client._call_siliconflow_with_meta(
        sf_client._EVALUATE_RESUME_PROMPT,
        json_like_text,
        model,
        False,  # 与原路由一致：无需额外 meta
    )
    if isinstance(content, str):
        return content
    try:
        return json.dumps(content, ensure_ascii=False)
    except Exception:
        return str(content)


TOOL_DESC = """评估/分析一份简历数据（JSON）。参数：
- data: 简历数据，dict/list/JSON字符串均可
- model: 使用的模型名（如 deepseek_v3）
返回：
- 将评估结果写入 state['resume_evaluation']，并追加一条 ToolMessage。
"""

@tool(description=TOOL_DESC)
def evaluate_resume_tool(
    data: Any,
    model: str = "deepseek_v3",
    state: Annotated[Dict, InjectedState] = None,
    tool_call_id: Annotated[str, InjectedToolCallId] = "",
) -> Command:
    """
    最小依赖版本：仅接收 data 与 model，返回评估结果。
    不做用户校验 / 不写数据库。
    """
    try:
        text = _serialize_data_to_text(data)
        if not text.strip():
            raise ValueError("请输入非空的简历数据。")

        evaluated = _llm_evaluate_resume(text, model)

        return Command(
            update={
                "resume_evaluation": evaluated,  # 单次结果：state['resume_evaluation']
                "messages": [
                    ToolMessage(
                        f"Resume evaluated successfully with model={model}.",
                        tool_call_id=tool_call_id,
                    )
                ],
            }
        )
    except Exception as e:
        return Command(
            update={
                "messages": [
                    ToolMessage(f"Failed to evaluate resume: {e}", tool_call_id=tool_call_id)
                ]
            }
        )
