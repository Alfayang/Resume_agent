# app/tools/parse_resume_tool.py
from __future__ import annotations
import base64
import json
from typing import Annotated, Dict, Any
import fitz  # PyMuPDF
from langchain_core.tools import tool, InjectedToolCallId
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState
from deepagents.siliconflow_client import sf_client
def _parse_pdf_bytes(pdf_bytes: bytes) -> str:
    """把 PDF 字节提取为纯文本（简单拼接每页文本）"""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    extracted = []
    for page in doc:
        extracted.append(page.get_text())
    text = "".join(extracted)
    if not text.strip():
        raise ValueError("无法从PDF中提取任何文本。")
    return text


def _llm_parse_resume(text: str, model: str) -> Dict[str, Any]:
    """
    调用 LLM（SiliconFlow）解析简历文本，返回 JSON 结果（dict）。
    这里假设 sf_client 返回 (content, meta)，content 为 dict 或 str。
    """
    content, meta = sf_client._call_siliconflow_with_meta(
        sf_client._PARSE_RESUME_PROMPT,
        text,
        model,
        True,  # return_meta
    )
    # 统一返回为 dict
    if isinstance(content, dict):
        return content
    # 若是字符串，尝试解析为 JSON；否则包装一下
    try:
        return json.loads(content)
    except Exception:
        return {"result": content, "meta": meta}


TOOL_DESC = """上传 PDF（以 base64 形式），解析简历信息并返回 JSON。
参数：
- pdf_b64: base64 编码的 PDF 文件内容
- model: 解析所用模型名（例如 deepseek_v3）
返回：
- 将解析结果写入 state['resume_parse']，并追加一条 ToolMessage。
"""

@tool(description=TOOL_DESC)
def parse_resume_tool(
    pdf_b64: str,
    model: str = "deepseek_v3",
    state: Annotated[dict, InjectedState] = None,
    tool_call_id: Annotated[str, InjectedToolCallId] = "",
) -> Command:
    """
    最小依赖：仅接收 PDF(base64) 和模型名，返回解析 JSON（写入 state）。
    不做用户校验、数据库写入。
    """
    try:
        pdf_bytes = base64.b64decode(pdf_b64)
        text = _parse_pdf_bytes(pdf_bytes)
        result = _llm_parse_resume(text, model)

        # 把结果放进 state（单一结果，用 'resume_parse'）
        update = {
            "resume_parse": result,
            "messages": [
                ToolMessage(
                    f"Resume parsed successfully with model={model}.",
                    tool_call_id=tool_call_id,
                )
            ],
        }
        return Command(update=update)

    except Exception as e:
        # 失败时也返回 ToolMessage，方便上层策略处理
        return Command(
            update={
                "messages": [
                    ToolMessage(f"Failed to parse resume: {e}", tool_call_id=tool_call_id)
                ]
            }
        )
