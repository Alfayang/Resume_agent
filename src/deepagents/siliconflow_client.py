# src/deepagents/services/siliconflow_client.py
from __future__ import annotations
import os, json, requests
from typing import Tuple, Any, Dict, Optional

# 可选：支持 .env（pip install python-dotenv）
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

SILICONFLOW_API_URL = os.getenv(
    "SILICONFLOW_API_URL",
    "https://api.siliconflow.cn/v1/chat/completions"
)
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY")  # 必填

class _Prompts:
    _CONTRACT_TEXT_PROMPT = "请在保留关键信息的前提下精简以下文本："
    _REWRITE_TEXT_PROMPT = "请对以下文本进行润色，使其更清晰自然："
    _EXPAND_TEXT_PROMPT = "请对以下文本进行扩写，补充必要细节："
    _PARSE_RESUME_PROMPT = "请从以下简历文本中提取结构化信息并返回JSON："
    _EVALUATE_RESUME_PROMPT = "请对以下简历JSON给出评价与改进建议："
    _GENERATE_STATEMENT_PROMPT = "根据以下信息生成个人陈述（尽量结构化）："
    _GENERATE_RECOMMENDATION_PROMPT = "根据以下信息生成推荐信（返回JSON结构）："
    _NAME_DOCUMENT_PROMPT = "请为以下Markdown文档生成一个简洁贴切的标题："

class SiliconFlowClient(_Prompts):
    def __init__(self, api_url: str, api_key: Optional[str]) -> None:
        if not api_key:
            raise RuntimeError(
                "SILICONFLOW_API_KEY 未设置。请在环境变量或 .env 中配置。"
            )
        self.api_url = api_url
        self.api_key = api_key

    def _call_siliconflow_with_meta(
        self,
        system_prompt: str,
        user_text: str,
        model: str,
        return_meta: bool = False,
    ) -> Tuple[Any, Dict[str, Any]]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            "temperature": 0.3,
            "stream": False,
        }
        resp = requests.post(self.api_url, headers=headers, data=json.dumps(payload), timeout=60)
        resp.raise_for_status()
        data = resp.json()

        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = data.get("usage", {})
        meta = {
            "system_prompt": system_prompt,
            "model": model,
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
        }

        # 某些任务需要 JSON：尝试解析（失败就保持字符串）
        try:
            content = json.loads(content)
        except Exception:
            pass

        # 无论 return_meta True/False，都返回 (content, meta) 以兼容你现有工具
        return content, meta

# 导出一个单例
sf_client = SiliconFlowClient(SILICONFLOW_API_URL, SILICONFLOW_API_KEY)
