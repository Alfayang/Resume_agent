from langchain_openai import ChatOpenAI
import os

from dotenv import load_dotenv

# 先加载 .env 文件
load_dotenv()

def get_default_model():
 
    base_url = os.getenv("API_BASE_URL")
    api_key = os.getenv("API_KEY")
    return ChatOpenAI(
        model="o3",
        base_url=base_url,
        api_key=api_key,
        max_tokens=4096,   # 或更高，根据模型限制
        # temperature=0.7,
        #改动o3 不支持自定义 temperature
    )