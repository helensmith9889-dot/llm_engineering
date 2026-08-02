import os
from dotenv import load_dotenv
from IPython.display import Markdown, display
from openai import OpenAI

# 核心步骤：加载 API 密钥
load_dotenv(override=True)

# 步骤 1：编写提示词

system_prompt = "You are a helpful assistant that can help me with my stock fundamentals analysis."
user_prompt = """
    Give me the fundamentals of the stock AMZN. This includes the P/E ratio, EPS, ROE, and other relevant metrics.
    Give the results as numerical values without your commentary. Give the result as JSON format.
"""

# 步骤 2：组装 messages 列表

messages = [
    {"role" : "system", "content" : system_prompt},
    {"role" : "user", "content" : user_prompt}
] # 在此填写

# 步骤 3：通过 OpenAI 兼容接口调用本地 Ollama
OLLAMA_BASE_URL = "http://localhost:11434/v1"

ollama = OpenAI(base_url=OLLAMA_BASE_URL, api_key='ollama')

response = ollama.chat.completions.create(model="llama3.2", messages=messages)

# 步骤 4：打印结果
print(response.choices[0].message.content)
