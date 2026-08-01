"""
Week 5 RAG（Retrieval-Augmented Generation，检索增强生成）评估仪表盘。

RAG 一句话：先从知识库「检索」相关段落，再让 LLM「生成」答案。
评估也要拆成两段问：
  1. Retrieval evaluation（检索评估）：向量数据库（vector DB）找回来的文档对不对、排得前不前？
     指标：MRR、nDCG、Keyword Coverage（详见 evaluation/eval.py 的公式注释）。
  2. Answer evaluation（答案评估）：最终回答准不准、全不全、贴不贴题？
     用 LLM-as-a-judge（大模型当裁判）打 Accuracy / Completeness / Relevance（1–5 分）。

本文件负责 Gradio UI（按钮、进度条、彩色指标卡、柱状图）；
真正算分的逻辑在 evaluation/eval.py。

在 Week 5 管线中的位置：
  ingest → vector DB → answer → evaluation（本文件是评估 UI）
"""

import gradio as gr
import pandas as pd
from collections import defaultdict
from dotenv import load_dotenv

from evaluation.eval import evaluate_all_retrieval, evaluate_all_answers

load_dotenv(override=True)

# ---------- 检索指标（retrieval metrics）颜色阈值 ----------
# 超过「绿」阈值 → 仪表盘显示绿色；介于绿/橙之间 → 橙色；更低 → 红色
# MRR（Mean Reciprocal Rank，平均倒数排名）：越接近 1 越好（相关内容越靠前）
MRR_GREEN = 0.9
MRR_AMBER = 0.75
# nDCG（Normalized Discounted Cumulative Gain，归一化折损累积增益）
NDCG_GREEN = 0.9
NDCG_AMBER = 0.75
# Keyword Coverage（关键词覆盖率，百分比）：期望关键词里有多少至少被检索命中
COVERAGE_GREEN = 90.0
COVERAGE_AMBER = 75.0

# ---------- 答案指标（answer metrics，1–5 分制）颜色阈值 ----------
ANSWER_GREEN = 4.5
ANSWER_AMBER = 4.0


def get_color(value: float, metric_type: str) -> str:
    """
    根据指标类型与数值返回绿/橙/红颜色名，用于仪表盘视觉提示。

    不同指标量纲不同（MRR/nDCG 在 0–1，Coverage 是百分比，答案分是 1–5），
    所以要用 metric_type 选择对应阈值，不能用同一套数字硬套。

    参数:
        value: 指标数值
        metric_type: "mrr" | "ndcg" | "coverage" | "accuracy" | "completeness" | "relevance"
    """
    if metric_type == "mrr":
        if value >= MRR_GREEN:
            return "green"
        elif value >= MRR_AMBER:
            return "orange"
        else:
            return "red"
    elif metric_type == "ndcg":
        if value >= NDCG_GREEN:
            return "green"
        elif value >= NDCG_AMBER:
            return "orange"
        else:
            return "red"
    elif metric_type == "coverage":
        if value >= COVERAGE_GREEN:
            return "green"
        elif value >= COVERAGE_AMBER:
            return "orange"
        else:
            return "red"
    elif metric_type in ["accuracy", "completeness", "relevance"]:
        if value >= ANSWER_GREEN:
            return "green"
        elif value >= ANSWER_AMBER:
            return "orange"
        else:
            return "red"
    return "black"


def format_metric_html(
    label: str,
    value: float,
    metric_type: str,
    is_percentage: bool = False,
    score_format: bool = False,
) -> str:
    """
    将单个评估指标渲染为带颜色边框的 HTML 卡片。

    参数:
        label: 显示名称（如 "Mean Reciprocal Rank (MRR)"）
        value: 数值
        metric_type: 传给 get_color 的类型键
        is_percentage: True 时按百分比显示（Keyword Coverage）
        score_format: True 时按「x.xx/5」显示（答案质量分）
    """
    color = get_color(value, metric_type)
    if is_percentage:
        value_str = f"{value:.1f}%"
    elif score_format:
        value_str = f"{value:.2f}/5"
    else:
        value_str = f"{value:.4f}"
    return f"""
    <div style="margin: 10px 0; padding: 15px; background-color: #f5f5f5; border-radius: 8px; border-left: 5px solid {color};">
        <div style="font-size: 14px; color: #666; margin-bottom: 5px;">{label}</div>
        <div style="font-size: 28px; font-weight: bold; color: {color};">{value_str}</div>
    </div>
    """


def run_retrieval_evaluation(progress=gr.Progress()):
    """
    运行全部测试题的检索评估，汇总 MRR / nDCG / Keyword Coverage。

    底层由 evaluate_all_retrieval 逐题调用 fetch_context（向量检索），
    检查期望 keywords 是否出现在检索结果中、排在第几位。

    为什么还要按 category 分组画柱状图？
      不同题型（如 direct_fact、spanning）难度不同；总体平均好看时，
      某一类可能仍然很差——分组 MRR 帮你定位薄弱环节。

    返回:
        (汇总指标 HTML, 按 category 分组的平均 MRR 柱状图数据 DataFrame)
    """
    total_mrr = 0.0
    total_ndcg = 0.0
    total_coverage = 0.0
    category_mrr = defaultdict(list)
    count = 0

    for test, result, prog_value in evaluate_all_retrieval():
        count += 1
        total_mrr += result.mrr
        total_ndcg += result.ndcg
        total_coverage += result.keyword_coverage

        # 按题目类别（如 direct_fact、spanning）累计 MRR，便于发现薄弱类型
        category_mrr[test.category].append(result.mrr)

        # Update progress bar only（英文 desc 是 Gradio UI 文案，保持原样）
        progress(prog_value, desc=f"Evaluating test {count}...")

    # Calculate final averages：总数除以题目数得到宏平均
    avg_mrr = total_mrr / count
    avg_ndcg = total_ndcg / count
    avg_coverage = total_coverage / count

    # Create final summary metrics HTML
    final_html = f"""
    <div style="padding: 0;">
        {format_metric_html("Mean Reciprocal Rank (MRR)", avg_mrr, "mrr")}
        {format_metric_html("Normalized DCG (nDCG)", avg_ndcg, "ndcg")}
        {format_metric_html("Keyword Coverage", avg_coverage, "coverage", is_percentage=True)}
        <div style="margin-top: 20px; padding: 10px; background-color: #d4edda; border-radius: 5px; text-align: center; border: 1px solid #c3e6cb;">
            <span style="font-size: 14px; color: #155724; font-weight: bold;">✓ Evaluation Complete: {count} tests</span>
        </div>
    </div>
    """

    # Create final bar chart data：每个 category 一行，供 Gradio BarPlot 使用
    category_data = []
    for category, mrr_scores in category_mrr.items():
        avg_cat_mrr = sum(mrr_scores) / len(mrr_scores)
        category_data.append({"Category": category, "Average MRR": avg_cat_mrr})

    df = pd.DataFrame(category_data)

    return final_html, df


def run_answer_evaluation(progress=gr.Progress()):
    """
    运行全部测试题的答案评估（LLM-as-a-judge）。

    每题走完整 RAG：检索 → 生成答案 → 裁判模型对照 reference_answer 打分。
    指标：Accuracy（准确性）、Completeness（完整性）、Relevance（相关性）。

    注意：比纯检索评估更慢、更贵（每题至少两次 LLM 调用：答题 + 裁判）。

    返回:
        (汇总指标 HTML, 按 category 分组的平均 Accuracy 柱状图数据 DataFrame)
    """
    total_accuracy = 0.0
    total_completeness = 0.0
    total_relevance = 0.0
    category_accuracy = defaultdict(list)
    count = 0

    for test, result, prog_value in evaluate_all_answers():
        count += 1
        total_accuracy += result.accuracy
        total_completeness += result.completeness
        total_relevance += result.relevance

        category_accuracy[test.category].append(result.accuracy)

        # Update progress bar only
        progress(prog_value, desc=f"Evaluating test {count}...")

    # Calculate final averages
    avg_accuracy = total_accuracy / count
    avg_completeness = total_completeness / count
    avg_relevance = total_relevance / count

    # Create final summary metrics HTML
    final_html = f"""
    <div style="padding: 0;">
        {format_metric_html("Accuracy", avg_accuracy, "accuracy", score_format=True)}
        {format_metric_html("Completeness", avg_completeness, "completeness", score_format=True)}
        {format_metric_html("Relevance", avg_relevance, "relevance", score_format=True)}
        <div style="margin-top: 20px; padding: 10px; background-color: #d4edda; border-radius: 5px; text-align: center; border: 1px solid #c3e6cb;">
            <span style="font-size: 14px; color: #155724; font-weight: bold;">✓ Evaluation Complete: {count} tests</span>
        </div>
    </div>
    """

    # Create final bar chart data
    category_data = []
    for category, accuracy_scores in category_accuracy.items():
        avg_cat_accuracy = sum(accuracy_scores) / len(accuracy_scores)
        category_data.append({"Category": category, "Average Accuracy": avg_cat_accuracy})

    df = pd.DataFrame(category_data)

    return final_html, df


def main():
    """
    启动 Gradio RAG 评估仪表盘：上半区检索评估，下半区答案评估。

    Gradio Blocks：用 Python 声明式拼 UI；button.click 把函数接到组件 outputs 上。
    """
    theme = gr.themes.Soft(font=["Inter", "system-ui", "sans-serif"])

    with gr.Blocks(title="RAG Evaluation Dashboard", theme=theme) as app:
        gr.Markdown("# 📊 RAG Evaluation Dashboard")
        gr.Markdown("Evaluate retrieval and answer quality for the Insurellm RAG system")

        # RETRIEVAL SECTION — 评估「找没找对文档」
        gr.Markdown("## 🔍 Retrieval Evaluation")

        retrieval_button = gr.Button("Run Evaluation", variant="primary", size="lg")

        with gr.Row():
            with gr.Column(scale=1):
                retrieval_metrics = gr.HTML(
                    "<div style='padding: 20px; text-align: center; color: #999;'>Click 'Run Evaluation' to start</div>"
                )

            with gr.Column(scale=1):
                # y_lim=[0,1]：MRR 理论范围；柱状图便于对比各类题
                retrieval_chart = gr.BarPlot(
                    x="Category",
                    y="Average MRR",
                    title="Average MRR by Category",
                    y_lim=[0, 1],
                    height=400,
                )

        # ANSWERING SECTION — 评估「答得好不好」
        gr.Markdown("## 💬 Answer Evaluation")

        answer_button = gr.Button("Run Evaluation", variant="primary", size="lg")

        with gr.Row():
            with gr.Column(scale=1):
                answer_metrics = gr.HTML(
                    "<div style='padding: 20px; text-align: center; color: #999;'>Click 'Run Evaluation' to start</div>"
                )

            with gr.Column(scale=1):
                # 答案分是 1–5，所以 y 轴从 1 起更直观
                answer_chart = gr.BarPlot(
                    x="Category",
                    y="Average Accuracy",
                    title="Average Accuracy by Category",
                    y_lim=[1, 5],
                    height=400,
                )

        # Wire up the evaluations：点击按钮 → 跑评估函数 → 刷新 HTML + 图
        retrieval_button.click(
            fn=run_retrieval_evaluation,
            outputs=[retrieval_metrics, retrieval_chart],
        )

        answer_button.click(
            fn=run_answer_evaluation,
            outputs=[answer_metrics, answer_chart],
        )

    app.launch(inbrowser=True)


if __name__ == "__main__":
    main()
