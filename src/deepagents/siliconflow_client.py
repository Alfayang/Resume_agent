# src/deepagents/services/siliconflow_client.py
from __future__ import annotations
import os
import json
from typing import Tuple, Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 可选：.env 支持
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name)
    return v if v not in (None, "") else default


# === 可配置项（通过环境变量覆盖） ===
SILICONFLOW_BASE_URL = _env("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn")
SILICONFLOW_API_PATH = _env("SILICONFLOW_API_PATH", "/v1/chat/completions")
SILICONFLOW_API_KEY = _env("SILICONFLOW_API_KEY")  # 必填
SILICONFLOW_TIMEOUT = float(_env("SILICONFLOW_TIMEOUT", "60"))
SILICONFLOW_MAX_RETRIES = int(_env("SILICONFLOW_MAX_RETRIES", "3"))
SILICONFLOW_BACKOFF_FACTOR = float(_env("SILICONFLOW_BACKOFF_FACTOR", "0.5"))


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
    """
    多实例友好：
    - 每个进程各自持有一个 Session（连接复用，线程安全）
    - 无可变全局状态（可横向扩容）
    - 带自动重试和超时
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_path: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        backoff_factor: Optional[float] = None,
    ) -> None:
        base_url = base_url or SILICONFLOW_BASE_URL
        api_path = api_path or SILICONFLOW_API_PATH
        api_key = api_key or SILICONFLOW_API_KEY
        timeout = timeout or SILICONFLOW_TIMEOUT
        max_retries = max_retries if max_retries is not None else SILICONFLOW_MAX_RETRIES
        backoff_factor = backoff_factor if backoff_factor is not None else SILICONFLOW_BACKOFF_FACTOR

        if not api_key:
            raise RuntimeError("SILICONFLOW_API_KEY 未设置。请在环境变量或 .env 中配置。")

        # 组合最终 URL（避免双斜杠）
        self.api_url = f"{base_url.rstrip('/')}{api_path}"
        self.api_key = api_key
        self.timeout = timeout

        # Session + Retry（429/5xx 自动重试；只针对 POST）
        self.session = requests.Session()
        retry = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"],   # 只对 POST 生效
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })

    def _call_siliconflow_with_meta(
        self,
        system_prompt: str,
        user_text: str,
        model: str,
        return_meta: bool = False,
        *,
        force_json: bool = False,   # 若后端支持 JSON Mode，可置 True
        temperature: float = 0.3,
        extra_payload: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Any, Dict[str, Any]]:
        """
        与你现有工具兼容：返回 (content, meta)
        - content: 尝试 json.loads；失败则返回字符串
        - meta: 记录模型/用量等
        """
        payload: Dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            "temperature": temperature,
            "stream": False,
        }

        # 可选的 JSON 强约束（若 SiliconFlow/OpenAI 兼容端支持）
        if force_json:
            payload["response_format"] = {"type": "json_object"}

        if extra_payload:
            # 允许外部透传一些参数，例如 max_tokens / top_p 等
            payload.update(extra_payload)

        resp = self.session.post(self.api_url, json=payload, timeout=self.timeout)
        # 非 2xx 会在这里 raise
        resp.raise_for_status()

        # 容错解析
        try:
            data = resp.json()
        except Exception as e:
            raise RuntimeError(f"SiliconFlow 返回非 JSON：{e}; text={resp.text[:300]}")

        # OpenAI 兼容格式
        msg = (data.get("choices") or [{}])[0].get("message", {})
        content = msg.get("content", "")

        # usage 元信息
        usage = data.get("usage", {}) or {}
        meta = {
            "system_prompt": system_prompt,
            "model": model,
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
            "raw": data if return_meta else None,  # 需要时可返回原始响应
        }

        # 内容尽量转 JSON
        if isinstance(content, str):
            content_str = content.strip()
            # 如果是 JSON 字符串，尝试解析
            if content_str.startswith("{") or content_str.startswith("["):
                try:
                    content = json.loads(content_str)
                except Exception:
                    # 保持原字符串
                    pass

        return content, meta


# 导出一个单例（每个进程一份，无共享可变状态 → 多实例安全）
sf_client = SiliconFlowClient()
