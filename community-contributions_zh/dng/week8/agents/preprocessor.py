import os

from dotenv import load_dotenv
from openai import OpenAI

# 加载环境变量
load_dotenv(override=True)

MODEL = os.getenv("PRICER_PREPROCESSOR_MODEL", "qwen/qwen-2.5-7b-instruct")

SYSTEM_PROMPT = """Create a concise description of a product. Respond only in this format. Do not include part numbers.

Title: Rewritten short precise title
Category: eg Electronics
Brand: Brand name
Description: 1 sentence description
Details: 1 sentence on features
"""

# OpenRouter客户端（兼容OpenAI）
client = OpenAI(
    api_key=os.environ["OPENROUTER_API_KEY"],
    base_url="https://openrouter.ai/api/v1",
)


class Preprocessor:
    def __init__(self, model_name: str = MODEL):
        self.model_name = model_name
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def messages_for(self, text: str) -> list[dict]:
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ]

    def preprocess(self, text: str) -> str:
        messages = self.messages_for(text)

        response = client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=0.2,  # lower for consistent dataset generation
        )

        # 跟踪令牌使用情况（如果提供）
        if response.usage:
            self.total_input_tokens += response.usage.prompt_tokens
            self.total_output_tokens += response.usage.completion_tokens

        return response.choices[0].message.content.strip()
