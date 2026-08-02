# 或许是增强版网页抓取：用本地 AI 模型分析托管网站的潜在漏洞

import os
from dotenv import load_dotenv
from openai import OpenAI
import requests

# 加载环境变量（本脚本主要用本地 Ollama）
load_dotenv(override=True)

base_url = "http://localhost:11434/v1"
api_key = "ollama"

# 通过 OpenAI 兼容接口连接本地 Ollama
client = OpenAI(
    base_url=base_url,
    api_key=api_key
)

def get_data_from_url(url: str):
    """请求 URL，优先返回 JSON，否则返回文本。"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        if "application/json" in response.headers.get("Content-Type", ""):
            return response.json()

        return response.text

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None


# 抓取个人网站内容
data = get_data_from_url("https://hashimalzuraiqi.me/")

# 构造分析提示：漏洞 / 可疑声明 / 要点列表
messages = [
    {
        "role": "system",
        "content": "You are a web analyzer and scraper. Analyze website content carefully."
    },
    {
        "role": "user",
        "content": f"""
Analyze this website content and summarize:

1. Possible security vulnerabilities or exposed information.
2. Any suspicious claims or indicators that the person might be exaggerating or lying.
3. Give the answer in simple clear points.

Website content:

{data}
"""
    }
]

response = client.chat.completions.create(
    model="llama3.2",
    messages=messages
)

print(response.choices[0].message.content)
