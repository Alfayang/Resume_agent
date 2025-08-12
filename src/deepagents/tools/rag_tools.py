# rag_tool.py
from langchain_core.tools import tool
import httpx

@tool(description="Query the knowledge base using RAG. Use this tool to retrieve stylistic human-written paragraphs.")
def rag_qa_tool(query: str, level: str = "paragraph", top_k: int = 5, uid: str = "") -> str:
    url = "http://localhost:8899/api/qa"  # 实际部署的 RAG 检索接口
    payload = {
        "query": query,
        "level": level,
        "top_k": top_k,
        "uid": uid
    }
    print(f"【DEBUG】rag_qa_tool被调用: query={query}, level={level}, top_k={top_k}, uid={uid}")
    try:
        resp = httpx.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("answer", "")  # 返回纯文本段落作为上下文
    except Exception as e:
        return f"[RAG Tool Error] {str(e)}"