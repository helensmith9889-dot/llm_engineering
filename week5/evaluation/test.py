"""
Week 5 RAG（Retrieval-Augmented Generation，检索增强生成）测试题数据模型。

本模块定义评估用的 TestQuestion，并从 JSONL（每行一个 JSON）加载题库。
每题包含：
  - question：发给 RAG 系统的问题
  - keywords：期望出现在检索 context 中的关键词（用于 retrieval metrics）
  - reference_answer：参考答案（用于 LLM-as-a-judge 的答案评估）
  - category：题型分类（如 direct_fact、spanning、temporal）

在 Week 5 管线中的位置：evaluation 的「标准答案/期望」侧；
与 ingest / vector DB / answer 解耦，只被 eval.py 与仪表盘读取。
"""

import json
from pathlib import Path
from pydantic import BaseModel, Field

# 测试文件与本模块同目录，默认 tests.jsonl
TEST_FILE = str(Path(__file__).parent / "tests.jsonl")


class TestQuestion(BaseModel):
    """
    一道 RAG 评估测试题：问题 + 检索期望关键词 + 参考答案 + 类别。

    keywords 用于检查 retrieval（向量检索）是否捞到了正确片段；
    reference_answer 用于答案侧的 Accuracy / Completeness / Relevance 打分。
    """

    question: str = Field(description="The question to ask the RAG system")
    keywords: list[str] = Field(description="Keywords that must appear in retrieved context")
    reference_answer: str = Field(description="The reference answer for this question")
    category: str = Field(description="Question category (e.g., direct_fact, spanning, temporal)")


def load_tests() -> list[TestQuestion]:
    """
    从 JSONL 文件加载全部 TestQuestion。

    JSONL：每一行是一个独立 JSON 对象，适合逐行追加测试用例。
    返回解析后的列表，供 evaluate_all_retrieval / evaluate_all_answers 遍历。
    """
    tests = []
    with open(TEST_FILE, "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line.strip())
            tests.append(TestQuestion(**data))
    return tests
