"""
Week 7 商品 Item：面向监督微调（SFT）的 prompt / completion 格式。

相对 Week 6，本周强调把每条商品变成「提示 + 补全」对：
- prompt：问题 +（可能截断的）摘要 + 「Price is $」
- completion：价格字符串（可四舍五入到美元）

这正是常见 LLM fine-tuning 数据格式。还提供 token 计数与 Hub 推送，
便于控制上下文长度、把数据集交给 Hugging Face Trainer / TRL 使用。
"""

from pydantic import BaseModel
from datasets import Dataset, DatasetDict, load_dataset
from typing import Optional, Self


PREFIX = "Price is $"
QUESTION = "What does this cost to the nearest dollar?"


class Item(BaseModel):
    """
    带价格的商品样本；Week 7 额外含 completion 字段供 SFT。

    字段速览：
    - summary：模型输入侧的产品描述
    - prompt / completion：拆开的「问」与「答」，训练时拼在一起学
    - full / weight：上游清洗遗留字段，可选
    """

    title: str
    category: str
    price: float
    full: Optional[str] = None
    weight: Optional[float] = None
    summary: Optional[str] = None
    prompt: Optional[str] = None
    completion: Optional[str] = None
    id: Optional[int] = None

    def make_prompt(self, text: str):
        """旧式一体 prompt：文本 + PREFIX + 真实价格（含答案）。"""
        self.prompt = f"{QUESTION}\n\n{text}\n\n{PREFIX}{round(self.price)}.00"

    def test_prompt(self) -> str:
        """推理时截掉答案，只保留到 PREFIX。"""
        return self.prompt.split(PREFIX)[0] + PREFIX

    def __repr__(self) -> str:
        return f"<{self.title} = ${self.price}>"

    @staticmethod
    def push_to_hub(dataset_name: str, train: list[Self], val: list[Self], test: list[Self]):
        """把完整 Item 字段推到 Hub（含 title/price/summary 等）。"""
        DatasetDict(
            {
                "train": Dataset.from_list([item.model_dump() for item in train]),
                "validation": Dataset.from_list([item.model_dump() for item in val]),
                "test": Dataset.from_list([item.model_dump() for item in test]),
            }
        ).push_to_hub(dataset_name)

    @classmethod
    def from_hub(cls, dataset_name: str) -> tuple[list[Self], list[Self], list[Self]]:
        """从 Hub 还原 train / validation / test 三个 Item 列表。"""
        ds = load_dataset(dataset_name)
        return (
            [cls.model_validate(row) for row in ds["train"]],
            [cls.model_validate(row) for row in ds["validation"]],
            [cls.model_validate(row) for row in ds["test"]],
        )

    def count_tokens(self, tokenizer):
        """
        统计 summary 的 token 数（不含特殊符号）。

        Token：分词器把文本切成的小块，是 LLM 计费与上下文窗口的基本单位。
        """
        return len(tokenizer.encode(self.summary, add_special_tokens=False))

    def make_prompts(self, tokenizer, max_tokens, do_round):
        """
        按 max_tokens 截断 summary，再生成分离的 prompt 与 completion。

        参数:
            tokenizer: Hugging Face 分词器
            max_tokens: 摘要允许的最大 token 数（控制训练序列长度）
            do_round: True 则 completion 为「整数美元.00」，否则用原始 price 字符串
        """
        tokens = tokenizer.encode(self.summary, add_special_tokens=False)
        if len(tokens) > max_tokens:
            # 先截 token 再 decode，避免硬截字符串切坏多字节/子词边界
            summary = tokenizer.decode(tokens[:max_tokens]).rstrip()
        else:
            summary = self.summary
        self.prompt = f"{QUESTION}\n\n{summary}\n\n{PREFIX}"
        self.completion = f"{round(self.price)}.00" if do_round else str(self.price)

    def count_prompt_tokens(self, tokenizer):
        """统计 prompt+completion 总 token，用于估算训练序列长度。"""
        full = self.prompt + self.completion
        tokens = tokenizer.encode(full, add_special_tokens=False)
        return len(tokens)

    def to_datapoint(self) -> dict:
        """转成 SFT 常用字典：仅 prompt 与 completion 两列。"""
        return {"prompt": self.prompt, "completion": self.completion}

    @staticmethod
    def push_prompts_to_hub(
        dataset_name: str, train: list[Self], val: list[Self], test: list[Self]
    ):
        """
        以 prompt-completion 格式推送数据集，直接对接 SFT 训练脚本。

        注意划分键名为 train / val / test（与完整 Item 推送的 validation 命名略有不同）。
        """
        DatasetDict(
            {
                "train": Dataset.from_list([item.to_datapoint() for item in train]),
                "val": Dataset.from_list([item.to_datapoint() for item in val]),
                "test": Dataset.from_list([item.to_datapoint() for item in test]),
            }
        ).push_to_hub(dataset_name)
