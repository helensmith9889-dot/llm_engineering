"""
文本预处理器：在 Ensemble 估价前，把杂乱商品描述改写成统一短结构。

为什么需要 Preprocessor？
  Scanner / RSS 来的描述长短不一、营销话术多；三个定价模型若吃到不同风格输入，
  误差会放大。先用一个小 LLM（默认 Ollama 本地 llama3.2）改写成：
    Title / Category / Brand / Description / Details
  再交给 Specialist / Frontier / NeuralNetwork，输入分布更稳定。

教学要点：LiteLLM 统一调用多家模型；api_base 指向本地 Ollama；统计 token 与费用。
"""

from litellm import completion
from dotenv import load_dotenv
import os

load_dotenv(override=True)

# 可用环境变量 PRICER_PREPROCESSOR_MODEL 覆盖；默认走本地 Ollama
DEFAULT_MODEL_NAME = os.getenv("PRICER_PREPROCESSOR_MODEL", "ollama/llama3.2")
# 部分推理模型需要 reasoning_effort；其它模型设为 None
DEFAULT_REASONING_EFFORT = "low" if "gpt-oss" in DEFAULT_MODEL_NAME else None

# 改写格式说明（字面量保持英文，作为 system prompt）
SYSTEM_PROMPT = """Create a concise description of a product. Respond only in this format. Do not include part numbers.
Title: Rewritten short precise title
Category: eg Electronics
Brand: Brand name
Description: 1 sentence description
Details: 1 sentence on features"""


class Preprocessor:
    """
    调用 LLM 把原始商品文本规范化，并累计 token / 费用统计。
    """

    def __init__(
        self,
        model_name=DEFAULT_MODEL_NAME,
        reasoning_effort=DEFAULT_REASONING_EFFORT,
        base_url=None,
    ):
        """
        参数:
            model_name: LiteLLM 模型名（如 ollama/llama3.2）
            reasoning_effort: 可选推理强度
            base_url: API 基址；Ollama 默认 http://localhost:11434
        """
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0
        self.model_name = model_name
        self.reasoning_effort = reasoning_effort
        self.base_url = base_url
        if "ollama" in model_name and not base_url:
            self.base_url = "http://localhost:11434"

    def messages_for(self, text: str) -> list[dict]:
        """组装 system + user 两条消息。"""
        return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": text}]

    def preprocess(self, text: str) -> str:
        """
        对单条描述做改写。

        参数:
            text: 原始商品描述
        返回:
            模型改写后的规范化文本；同时累加 usage 与 response_cost。
        """
        messages = self.messages_for(text)
        response = completion(
            messages=messages,
            model=self.model_name,
            reasoning_effort=self.reasoning_effort,
            api_base=self.base_url,
        )
        self.total_input_tokens += response.usage.prompt_tokens
        self.total_output_tokens += response.usage.completion_tokens
        # LiteLLM 把费用放在隐藏参数里；本地 Ollama 通常为 0
        self.total_cost += response._hidden_params["response_cost"]
        return response.choices[0].message.content
