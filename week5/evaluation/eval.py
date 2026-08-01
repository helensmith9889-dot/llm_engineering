"""
Week 5 RAG（Retrieval-Augmented Generation，检索增强生成）评估核心逻辑。

本模块实现两类评估（evaluation metrics）：

1) Retrieval（检索）——只看「找文档」好不好，不看最终措辞：
   - MRR（Mean Reciprocal Rank，平均倒数排名）：
       相关关键词第一次出现在第 rank 位 → 得分 1/rank；未出现 → 0。
       例：排第 1 得 1.0，第 2 得 0.5。越高说明相关内容越靠前。
   - nDCG（Normalized Discounted Cumulative Gain，归一化折损累积增益）：
       越靠后的命中贡献越小（被 log 折损）；再用「理想排序」归一化到 0–1。
   - Keyword Coverage（关键词覆盖率）：期望关键词里有多少至少命中一次（百分比）。

2) Answer（答案）——看整条 RAG 答得好不好：
   - LLM-as-a-judge：另请一个模型当裁判，对照 reference answer（参考答案）
     给 Accuracy / Completeness / Relevance 打 1–5 分（结构化输出 AnswerEval）。

在 Week 5 管线中的位置：
  ingest → vector DB → answer（fetch_context / answer_question）→ 本模块评估
供 evaluator.py 仪表盘与命令行 `python eval.py <题号>` 调用。
"""

import sys
import math
from pydantic import BaseModel, Field
from litellm import completion
from dotenv import load_dotenv

from evaluation.test import TestQuestion, load_tests
from implementation.answer import answer_question, fetch_context


load_dotenv(override=True)

MODEL = "gpt-4.1-nano"
db_name = "vector_db"


class RetrievalEval(BaseModel):
    """
    检索性能评估指标的结构化结果（Pydantic 模型，便于序列化与类型检查）。

    字段说明见下方 Field(description=...)；这些英文 description 会参与 schema，勿改字面量。
    """

    mrr: float = Field(description="Mean Reciprocal Rank - average across all keywords")
    ndcg: float = Field(description="Normalized Discounted Cumulative Gain (binary relevance)")
    keywords_found: int = Field(description="Number of keywords found in top-k results")
    total_keywords: int = Field(description="Total number of keywords to find")
    keyword_coverage: float = Field(description="Percentage of keywords found")


class AnswerEval(BaseModel):
    """
    LLM-as-a-judge 对答案质量的结构化打分结果。

    用 response_format=AnswerEval 时，模型必须按此 schema 返回 JSON，
    比「自由文本里自己解析分数」稳定得多。
    """

    feedback: str = Field(
        description="Concise feedback on the answer quality, comparing it to the reference answer and evaluating based on the retrieved context"
    )
    accuracy: float = Field(
        description="How factually correct is the answer compared to the reference answer? 1 (wrong. any wrong answer must score 1) to 5 (ideal - perfectly accurate). An acceptable answer would score 3."
    )
    completeness: float = Field(
        description="How complete is the answer in addressing all aspects of the question? 1 (very poor - missing key information) to 5 (ideal - all the information from the reference answer is provided completely). Only answer 5 if ALL information from the reference answer is included."
    )
    relevance: float = Field(
        description="How relevant is the answer to the specific question asked? 1 (very poor - off-topic) to 5 (ideal - directly addresses question and gives no additional information). Only answer 5 if the answer is completely relevant to the question and gives no additional information."
    )


def calculate_mrr(keyword: str, retrieved_docs: list) -> float:
    """
    计算单个关键词的 Reciprocal Rank（倒数排名，case-insensitive）。

    在检索结果列表中，第一次出现该 keyword 的位置 rank（从 1 起）对应分数 1/rank；
    若未出现则返回 0。MRR 越高，说明相关内容越靠前。

    直觉：搜「退款政策」时，含关键词的段落如果排在第 1 名，MRR 贡献就是 1；
    若埋在第 10 名，只有 0.1——检索系统「找得到但排太后」也会被惩罚。
    """
    keyword_lower = keyword.lower()
    for rank, doc in enumerate(retrieved_docs, start=1):
        if keyword_lower in doc.page_content.lower():
            return 1.0 / rank
    return 0.0


def calculate_dcg(relevances: list[int], k: int) -> float:
    """
    计算 DCG（Discounted Cumulative Gain，折损累积增益）。

    位置越靠后，增益被 log2(rank+1) 折损越多——体现「排在前面更重要」。
    relevances[i] 为该位置的相关性（本课用 0/1 二值相关：命中关键词=1）。

    公式直觉：同样一次「命中」，出现在第 1 位几乎满分计入；出现在很后面几乎加不了多少。
    """
    dcg = 0.0
    for i in range(min(k, len(relevances))):
        # i+2 because rank starts at 1：i=0 → rank=1 → log2(2)=1，第一位不折损
        dcg += relevances[i] / math.log2(i + 2)
    return dcg


def calculate_ndcg(keyword: str, retrieved_docs: list, k: int = 10) -> float:
    """
    计算单个关键词的 nDCG（归一化 DCG，binary relevance，case-insensitive）。

    步骤：
      1. 构造 top-k 的 0/1 相关性序列（文档是否包含 keyword）
      2. 算实际排序的 DCG
      3. 把相关性序列按「最好可能」重排，算 IDCG（Ideal DCG）
      4. nDCG = DCG / IDCG（IDCG=0 表示 top-k 全无关 → 得 0）

    nDCG ∈ [0, 1]，1 表示在「有哪些文档相关」固定的前提下，相关文档已排在最优位置。
    """
    keyword_lower = keyword.lower()

    # Binary relevance: 1 if keyword found, 0 otherwise
    relevances = [
        1 if keyword_lower in doc.page_content.lower() else 0 for doc in retrieved_docs[:k]
    ]

    # DCG
    dcg = calculate_dcg(relevances, k)

    # Ideal DCG (best case: keyword in first position)
    # 把所有 1 排到最前，得到「理想排序」下的 DCG 上界
    ideal_relevances = sorted(relevances, reverse=True)
    idcg = calculate_dcg(ideal_relevances, k)

    return dcg / idcg if idcg > 0 else 0.0


def evaluate_retrieval(test: TestQuestion, k: int = 10) -> RetrievalEval:
    """
    评估一道测试题的检索性能。

    Args:
        test: TestQuestion object containing question and keywords
        k: Number of top documents to retrieve (default 10)

    Returns:
        RetrievalEval object with MRR, nDCG, and keyword coverage metrics

    说明（中文）:
        用与线上一致的 fetch_context 做向量检索，再对每个期望 keyword
        计算 MRR / nDCG，并统计 Keyword Coverage（至少命中一次的关键词占比）。
        多关键词时对分数取平均，避免某一题 keywords 特别多时主导总分。
    """
    # Retrieve documents using shared answer module（与线上答题同一检索入口）
    retrieved_docs = fetch_context(test.question)

    # Calculate MRR (average across all keywords)
    mrr_scores = [calculate_mrr(keyword, retrieved_docs) for keyword in test.keywords]
    avg_mrr = sum(mrr_scores) / len(mrr_scores) if mrr_scores else 0.0

    # Calculate nDCG (average across all keywords)
    ndcg_scores = [calculate_ndcg(keyword, retrieved_docs, k) for keyword in test.keywords]
    avg_ndcg = sum(ndcg_scores) / len(ndcg_scores) if ndcg_scores else 0.0

    # Calculate keyword coverage：MRR>0 表示该词至少在某一篇文档里出现过
    keywords_found = sum(1 for score in mrr_scores if score > 0)
    total_keywords = len(test.keywords)
    keyword_coverage = (keywords_found / total_keywords * 100) if total_keywords > 0 else 0.0

    return RetrievalEval(
        mrr=avg_mrr,
        ndcg=avg_ndcg,
        keywords_found=keywords_found,
        total_keywords=total_keywords,
        keyword_coverage=keyword_coverage,
    )


def evaluate_answer(test: TestQuestion) -> tuple[AnswerEval, str, list]:
    """
    用 LLM-as-a-judge 评估一道题的答案质量。

    Args:
        test: TestQuestion object containing question and reference answer

    Returns:
        Tuple of (AnswerEval object, generated_answer string, retrieved_docs list)

    说明（中文）:
        先跑完整 RAG（answer_question），再让裁判模型对照 reference_answer，
        对 Accuracy / Completeness / Relevance 打 1–5 分（结构化输出 AnswerEval）。

        为什么要用「另一个 LLM」打分？
          开放域答案很难用精确字符串匹配；人类逐题打分又太慢。
          Judge 模型读「问题 + 生成答案 + 参考答案」，按统一 rubric 打分。
    """
    # Get RAG response using shared answer module
    generated_answer, retrieved_docs = answer_question(test.question)

    # LLM judge prompt — 提示词为英文 string literal，勿改动
    judge_messages = [
        {
            "role": "system",
            "content": "You are an expert evaluator assessing the quality of answers. Evaluate the generated answer by comparing it to the reference answer. Only give 5/5 scores for perfect answers.",
        },
        {
            "role": "user",
            "content": f"""Question:
{test.question}

Generated Answer:
{generated_answer}

Reference Answer:
{test.reference_answer}

Please evaluate the generated answer on three dimensions:
1. Accuracy: How factually correct is it compared to the reference answer? Only give 5/5 scores for perfect answers.
2. Completeness: How thoroughly does it address all aspects of the question, covering all the information from the reference answer?
3. Relevance: How well does it directly answer the specific question asked, giving no additional information?

Provide detailed feedback and scores from 1 (very poor) to 5 (ideal) for each dimension. If the answer is wrong, then the accuracy score must be 1.""",
        },
    ]

    # Call LLM judge with structured outputs (async)
    # response_format=AnswerEval 要求模型返回符合该 schema 的 JSON
    judge_response = completion(model=MODEL, messages=judge_messages, response_format=AnswerEval)

    # 把 JSON 字符串解析/校验成 AnswerEval 实例
    answer_eval = AnswerEval.model_validate_json(judge_response.choices[0].message.content)

    return answer_eval, generated_answer, retrieved_docs


def evaluate_all_retrieval():
    """
    对测试集全部题目做检索评估，逐题 yield (test, result, progress)。

    使用生成器（yield）而不是一次返回列表：Gradio 进度条可以边跑边更新。
    progress 为 0–1 进度。
    """
    tests = load_tests()
    total_tests = len(tests)
    for index, test in enumerate(tests):
        result = evaluate_retrieval(test)
        progress = (index + 1) / total_tests
        yield test, result, progress


def evaluate_all_answers():
    """
    对测试集全部题目做答案评估，逐题 yield (test, AnswerEval, progress)。

    注意：每题都会调用 LLM 生成 + 裁判打分，耗时与费用高于纯检索评估。
    这里只 yield AnswerEval（取 evaluate_answer 返回元组的第 0 项）。
    """
    tests = load_tests()
    total_tests = len(tests)
    for index, test in enumerate(tests):
        result = evaluate_answer(test)[0]
        progress = (index + 1) / total_tests
        yield test, result, progress


def run_cli_evaluation(test_number: int):
    """
    命令行：对指定题号打印检索指标、生成答案与裁判打分。

    适合单题调试（debug）RAG 检索与生成问题——比跑完整仪表盘更快定位「哪一步坏了」。
    """
    # Load tests
    tests = load_tests("tests.jsonl")

    if test_number < 0 or test_number >= len(tests):
        print(f"Error: test_row_number must be between 0 and {len(tests) - 1}")
        sys.exit(1)

    # Get the test
    test = tests[test_number]

    # Print test info（英文 print 保持原样，便于与课程材料对照）
    print(f"\n{'=' * 80}")
    print(f"Test #{test_number}")
    print(f"{'=' * 80}")
    print(f"Question: {test.question}")
    print(f"Keywords: {test.keywords}")
    print(f"Category: {test.category}")
    print(f"Reference Answer: {test.reference_answer}")

    # Retrieval Evaluation
    print(f"\n{'=' * 80}")
    print("Retrieval Evaluation")
    print(f"{'=' * 80}")

    retrieval_result = evaluate_retrieval(test)

    print(f"MRR: {retrieval_result.mrr:.4f}")
    print(f"nDCG: {retrieval_result.ndcg:.4f}")
    print(f"Keywords Found: {retrieval_result.keywords_found}/{retrieval_result.total_keywords}")
    print(f"Keyword Coverage: {retrieval_result.keyword_coverage:.1f}%")

    # Answer Evaluation
    print(f"\n{'=' * 80}")
    print("Answer Evaluation")
    print(f"{'=' * 80}")

    answer_result, generated_answer, retrieved_docs = evaluate_answer(test)

    print(f"\nGenerated Answer:\n{generated_answer}")
    print(f"\nFeedback:\n{answer_result.feedback}")
    print("\nScores:")
    print(f"  Accuracy: {answer_result.accuracy:.2f}/5")
    print(f"  Completeness: {answer_result.completeness:.2f}/5")
    print(f"  Relevance: {answer_result.relevance:.2f}/5")
    print(f"\n{'=' * 80}\n")


def main():
    """命令行入口：uv run eval.py <题号>，对单题跑检索+答案评估。"""
    if len(sys.argv) != 2:
        print("Usage: uv run eval.py <test_row_number>")
        sys.exit(1)

    try:
        test_number = int(sys.argv[1])
    except ValueError:
        print("Error: test_row_number must be an integer")
        sys.exit(1)

    run_cli_evaluation(test_number)


if __name__ == "__main__":
    main()
