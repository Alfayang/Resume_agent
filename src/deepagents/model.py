from langchain_openai import ChatOpenAI
import os

def get_default_model():
    # 你自己的 SiliconFlow 兼容 OpenAI 协议的 endpoint
    # 也可以配置到环境变量
    base_url = "https://api.siliconflow.cn/v1"
    # 你的 token
    api_key = "sk-cvjjbwjtrdmaweotvfowtrzmjohczaadqwqlsmrxyxyhtcgo"

    return ChatOpenAI(
        model="zai-org/GLM-4.5",
        base_url=base_url,
        api_key=api_key,
        max_tokens=4096,   # 或更高，根据模型限制
        temperature=0.7,
    )