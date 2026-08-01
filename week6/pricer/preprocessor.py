"""
单条商品摘要预处理器：用 LLM 把长描述压成结构化短摘要。

与 batch.py 的关系：
- Preprocessor：同步、逐条调用（适合调试、小样本）；
- Batch：异步批量 API（适合全量数据、更省钱）。

在微调流水线中，摘要质量直接影响「模型看见的输入」——统一格式
（Title / Category / Brand / Description / Details）降低噪声，便于学习价格。
本类还累计 token 用量与费用，帮助理解 API 成本。
"""

from litellm import completion

# 默认通过 LiteLLM 路由到的 Groq 模型
DEFAULT_MODEL_NAME = "groq/openai/gpt-oss-20b"
# 推理强度：low 更快更便宜，适合摘要这类结构化任务
DEFAULT_REASONING_EFFORT = "low"

# 系统提示：强制固定输出模板，并禁止零件号（减少无用编号）
SYSTEM_PROMPT = """Create a concise description of a product. Respond only in this format. Do not include part numbers.
Title: Rewritten short precise title
Category: eg Electronics
Brand: Brand name
Description: 1 sentence description
Details: 1 sentence on features"""


class Preprocessor:
    """
    封装一次「商品全文 → 简洁摘要」的 chat completion 调用，并记账。

    total_* 字段方便在 notebook 里汇报：用了多少 token、花了多少钱。
    """

    def __init__(self, model_name=DEFAULT_MODEL_NAME, reasoning_effort=DEFAULT_REASONING_EFFORT):
        """
        参数:
            model_name: LiteLLM 模型标识
            reasoning_effort: 传给支持该参数的模型的推理力度
        """
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0
        self.model_name = model_name
        self.reasoning_effort = reasoning_effort

    def messages_for(self, text: str) -> list[dict]:
        """构造 OpenAI 风格 messages：system 定格式，user 塞商品原文。"""
        return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": text}]

    def preprocess(self, text: str) -> str:
        """
        调用 LLM 生成摘要，累加 usage / cost，返回助手文本内容。

        LiteLLM 的 completion 统一了多家供应商的调用方式，便于换模型做实验。
        """
        messages = self.messages_for(text)
        response = completion(
            messages=messages, model=self.model_name, reasoning_effort=self.reasoning_effort
        )
        self.total_input_tokens += response.usage.prompt_tokens
        self.total_output_tokens += response.usage.completion_tokens
        self.total_cost += response._hidden_params["response_cost"]
        return response.choices[0].message.content
