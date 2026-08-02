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

# 步骤 3：调用 OpenAI
openai = OpenAI()
response = openai.chat.completions.create(model="gpt-4.1-mini", messages=messages)

# 步骤 4：打印结果
print(response.choices[0].message.content)
