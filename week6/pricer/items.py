"""
商品数据单元（Item）与 Hugging Face Dataset 互操作。

微调定价模型时，一条训练样本通常是「文本描述 + 价格标签」。
本模块用 Pydantic 定义结构化商品对象，并支持 push/load 到 Hub，
方便在不同机器、不同周次之间复用同一套 train/val/test 划分。

与 LLM 训练的关系：
- make_prompt 生成「问答式」监督文本：问题 + 商品描述 + 「Price is $xx.00」；
- test_prompt 截掉答案部分，留给模型在推理时补全价格。
"""

from pydantic import BaseModel
from datasets import Dataset, DatasetDict, load_dataset
from typing import Optional, Self


# 答案前缀：模型被训练成在这个前缀后输出价格
PREFIX = "Price is $"
# 固定问句，构成 instruction-style 样本
QUESTION = "What does this cost to the nearest dollar?"


class Item(BaseModel):
    """
    一条带价格的商品数据点（data-point）。

    字段说明（给初学者）：
    - title / category / price：核心标签信息
    - full：清洗后的长文本描述（来自解析器）
    - summary：LLM 批量摘要后的短描述（训练常用）
    - prompt：拼好的监督微调（SFT）文本
    - id：在列表中的索引，批量 API 的 custom_id 会用到
    """

    title: str
    category: str
    price: float
    full: Optional[str] = None
    weight: Optional[float] = None
    summary: Optional[str] = None
    prompt: Optional[str] = None
    id: Optional[int] = None

    def make_prompt(self, text: str):
        """
        组装完整训练 prompt：问题 + 商品文本 + 带真实价格的答案前缀。

        例如：...Price is $199.00 —— 模型学习在 PREFIX 后生成数字。
        """
        self.prompt = f"{QUESTION}\n\n{text}\n\n{PREFIX}{round(self.price)}.00"

    def test_prompt(self) -> str:
        """
        推理用 prompt：保留到 PREFIX 为止，不泄露真实价格。

        训练用完整串，评估时用截断串，让模型自己「补全」价格。
        """
        return self.prompt.split(PREFIX)[0] + PREFIX

    def __repr__(self) -> str:
        """调试时友好显示：标题 = 价格。"""
        return f"<{self.title} = ${self.price}>"

    @staticmethod
    def push_to_hub(dataset_name: str, train: list[Self], val: list[Self], test: list[Self]):
        """
        把 train/val/test 三个 Item 列表推到 Hugging Face Hub。

        DatasetDict 对应机器学习标准三分法：训练、验证、测试。
        """
        DatasetDict(
            {
                "train": Dataset.from_list([item.model_dump() for item in train]),
                "validation": Dataset.from_list([item.model_dump() for item in val]),
                "test": Dataset.from_list([item.model_dump() for item in test]),
            }
        ).push_to_hub(dataset_name)

    @classmethod
    def from_hub(cls, dataset_name: str) -> tuple[list[Self], list[Self], list[Self]]:
        """从 Hub 下载 Dataset，用 model_validate 还原为 Item 列表三元组。"""
        ds = load_dataset(dataset_name)
        return (
            [cls.model_validate(row) for row in ds["train"]],
            [cls.model_validate(row) for row in ds["validation"]],
            [cls.model_validate(row) for row in ds["test"]],
        )
