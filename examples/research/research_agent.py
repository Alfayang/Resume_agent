# examples/research/server.py
import os
import sys
import json
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# 让 Python 找到 src/deepagents
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

# 导入工厂
try:
    from deepagents import create_deep_agent
except Exception:
    from deepagents.agent_factory import create_deep_agent  # noqa

# 导入工具（都在 src/deepagents/tools 下）
from deepagents.tools.text_parse_tool import parse_resume_text_tool
from deepagents.tools.rewrite_tool import rewrite_text_tool
from deepagents.tools.expand_tool import expand_text_tool
from deepagents.tools.compress_tool import contract_text_tool
from deepagents.tools.evaluate_resume_tool import evaluate_resume_tool
from deepagents.tools.generate_statement_tool import generate_statement_tool
from deepagents.tools.generate_recommend_tool import generate_recommendation_tool
from deepagents.tools.document_name_tool import name_document_tool

# 子代理
doc_writer_subagent = {
    "name": "doc-writer",
    "description": "文书/简历任务专家：解析、重写、扩写、精简、评估、生成个人陈述/推荐信、文档命名。",
    "prompt": (
        "你是一名专业的文书与简历助手。\n"
        "你将收到一个 JSON 指令，形如：{\"action\": \"...\", \"inputs\": {...}, \"model\": \"...\"}。\n\n"
        "【动作与处理】\n"
        "- action == \"rewrite_letter\"：使用 inputs.references（可选）与 inputs.letter（原文）进行改写；只输出改写后的最终文本。\n"
        "- action == \"expand\" / \"contract\"：对 inputs.text 进行扩写或压缩；只输出修改后的最终文本。\n"
        "- action == \"evaluate_resume\"：基于 inputs.data（简历 JSON）进行评价；输出评价/建议文本。\n"
        "- action == \"generate_statement\"：根据 inputs.text 生成个人陈述；输出最终结果（文本或结构化 JSON，依具体工具返回）。\n"
        "- action == \"generate_recommendation\"：根据 inputs.text 生成推荐信；输出最终结果（文本或结构化 JSON）。\n"
        "- action == \"name_document\"：根据 inputs.text（Markdown）生成简洁标题；只输出标题字符串。\n"
        "- action == \"parse_resume_text\"：将 inputs.text（简历纯文本）解析为结构化 JSON；只输出解析后的 JSON。\n\n"
        "【统一输出要求】务必只返回最终结果，不要包含解释、过程描述或多余标注。"
    ),
    "tools": [
        "parse_resume_text",
        "rewrite_text",
        "expand_text",
        "contract_text",
        "evaluate_resume",
        "generate_statement",
        "generate_recommendation",
        "name_document",
    ],
}

# 主 Agent 提示：要求通过 task 委派给 doc-writer
main_prompt = """
你是编排代理（orchestration agent）。
当接到用户的文书/简历类请求时，请优先调用 `task` 工具，将任务委派给子代理 `doc-writer`，
并以如下 JSON 作为 description 传入：
{
  "action": "<rewrite_letter | expand | contract | evaluate_resume | generate_statement | generate_recommendation | name_document | parse_resume_text>",
  "inputs": { ... },
  "model": "deepseek_v3"
}
最终响应只包含最终结果，不要附加解释与过程。
"""

# 创建主 Agent：只暴露 task（不让主 Agent 直接调用任何文书工具）
agent = create_deep_agent(
    tools=[
        parse_resume_text_tool,
        rewrite_text_tool,
        expand_text_tool,
        contract_text_tool,
        evaluate_resume_tool,
        generate_statement_tool,
        generate_recommendation_tool,
        name_document_tool,
    ],
    instructions=main_prompt,
    subagents=[doc_writer_subagent],
    expose_tools_to_main=False,   # ⭐ 主 Agent 只能看到 task
)

# FastAPI
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Question(BaseModel):
    user_input: str

def _pick_output(result):
    if isinstance(result, dict):
        for k in [
            "rewritten_text", "contracted_text", "expanded_text",
            "document_name", "generated_statement", "generated_recommendation",
        ]:
            v = result.get(k)
            if v:
                return v
        msgs = result.get("messages") or []
        for m in reversed(msgs):
            if hasattr(m, "content"):
                content = m.content
                addkw = getattr(m, "additional_kwargs", {}) or {}
            else:
                content = m.get("content")
                addkw = m.get("additional_kwargs", {}) or {}
            if not content:
                continue
            if isinstance(addkw, dict) and "tool_calls" in addkw:
                continue
            return content
    return str(result)

@app.post("/generate")
async def generate_report(question: Question):
    result = agent.invoke({"messages": [{"role": "user", "content": question.user_input}]})
    output = _pick_output(result)
    if isinstance(output, (dict, list)):
        output = json.dumps(output, ensure_ascii=False, indent=2, default=str)
    return {"rewritten_letter": output}

@app.get("/health")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(f"{__name__}:app", host="0.0.0.0", port=8001)
