"""
商品数据点 Item：连接「定价数据集」与 Hugging Face Hub。

在 Week 8 扫货系统中，Item 更多服务训练/评估阶段（与 Frontier 的向量库、
DNN 训练数据同源思路）：每条记录是「商品文本 + 真实价格」。

Prompt 约定（与微调 pricer 一致）：
  QUESTION + 商品文本 + PREFIX + 价格
测试时 test_prompt() 只保留到 PREFIX，让模型续写价格数字。

教学关键词：Dataset / DatasetDict、model_dump、push_to_hub / load_dataset。
"""

from pydantic import BaseModel
from datasets import Dataset, DatasetDict, load_dataset
from typing import Optional, Self


# 微调/推理时共用的提示词片段（字面量勿改，需与 Modal pricer 服务一致）
PREFIX = "Price is $"
QUESTION = "What does this cost to the nearest dollar?"


class Item(BaseModel):
    """
    An Item is a data-point of a Product with a Price

    字段说明：
      title / category / price：核心标签
      full / summary / prompt：可选的长文本与已拼好的训练 prompt
      weight / id：可选元数据
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
        根据给定商品文本生成训练用完整 prompt（末尾含四舍五入后的价格）。

        参数:
            text: 写入问答中间的商品描述
        """
        self.prompt = f"{QUESTION}\n\n{text}\n\n{PREFIX}{round(self.price)}.00"

    def test_prompt(self) -> str:
        """
        生成测试用 prompt：截掉答案价格，只留到 PREFIX，供模型续写。
        """
        return self.prompt.split(PREFIX)[0] + PREFIX

    def __repr__(self) -> str:
        """简短展示：标题 = $价格。"""
        return f"<{self.title} = ${self.price}>"

    @staticmethod
    def push_to_hub(dataset_name: str, train: list[Self], val: list[Self], test: list[Self]):
        """
        Push Item lists to HuggingFace Hub

        把 train/val/test 三个列表转成 DatasetDict 并上传，便于复现实验。
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
        """
        Load from HuggingFace Hub and reconstruct Items

        返回:
            (train_list, validation_list, test_list)
        """
        ds = load_dataset(dataset_name)
        return (
            [cls.model_validate(row) for row in ds["train"]],
            [cls.model_validate(row) for row in ds["validation"]],
            [cls.model_validate(row) for row in ds["test"]],
        )
