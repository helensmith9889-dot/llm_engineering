"""
价格模型评估模块（Week 6）。

在微调 / DNN / LLM 提示工程中，「评估」回答一个朴素问题：
  模型猜的价格离真实价有多远？

本模块并行跑一批测试点，计算：
  - 平均绝对误差（MAE / Error）：|猜 − 真| 的平均，单位美元
  - 均方误差（MSE）：误差平方的平均，对离谱大错更敏感
  - R²（决定系数）：相对「永远猜均值」好多少；这里 *100 显示成百分比风格
并用散点图与累计误差曲线做可视化——这是定价任务的核心指标面板。

与 LLM 训练的关系：微调前后都用同一套评估，才能公平对比基线 vs 微调模型。
「感觉更聪明」不算数；同一测试集 + 同一指标才算数。
"""

import re
from sklearn.metrics import mean_squared_error, r2_score
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from itertools import accumulate
import math
from tqdm.notebook import tqdm
from concurrent.futures import ThreadPoolExecutor

# 终端彩色输出：绿/黄/红表示误差好坏
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
COLOR_MAP = {"red": RED, "orange": YELLOW, "green": GREEN}

# 默认并行线程数与评估样本数
# 线程适合「等 API」型预测：CPU 不算重，但网络等待可以重叠
WORKERS = 5
DEFAULT_SIZE = 200


class Tester:
    """
    对任意「预测函数」做端到端评估。

    predictor(datapoint) → 价格（数字或含 $ 的字符串）；
    data 是带 .price / .title 的 Item 列表。
    """

    def __init__(self, predictor, data, title=None, size=DEFAULT_SIZE, workers=WORKERS):
        """
        参数:
            predictor: 可调用对象，输入一个数据点，输出价格猜测
            data: 测试集列表
            title: 图表标题；默认从预测函数名美化生成
            size: 评估前 size 个样本（不必跑完整测试集）
            workers: 线程池大小（适合 I/O 型 LLM API 预测）
        """
        self.predictor = predictor
        self.data = data
        self.title = title or self.make_title(predictor)
        self.size = size
        self.titles = []
        self.guesses = []
        self.truths = []
        self.errors = []
        self.colors = []
        self.workers = workers

    @staticmethod
    def make_title(predictor) -> str:
        """把函数名转成可读标题，例如 gpt_4o_mini → Gpt 4O Mini（再替换 GPT）。"""
        return predictor.__name__.replace("__", ".").replace("_", " ").title().replace("Gpt", "GPT")

    @staticmethod
    def post_process(value):
        """
        把模型输出规范成 float。

        LLM 常返回「$1,299.00」之类字符串：去掉货币符号与逗号，再正则提取数字。
        抓不到数字时返回 0，避免评估循环崩溃（该点误差会很大，图上会很显眼）。
        """
        if isinstance(value, str):
            value = value.replace("$", "").replace(",", "")
            match = re.search(r"[-+]?\d*\.\d+|\d+", value)
            return float(match.group()) if match else 0
        else:
            return value

    def color_for(self, error, truth):
        """
        按绝对误差或相对误差给点上色：
        绿=较好，橙=中等，红=较差。阈值是课程经验值，非唯一标准。
        """
        if error < 40 or error / truth < 0.2:
            return "green"
        elif error < 80 or error / truth < 0.4:
            return "orange"
        else:
            return "red"

    def run_datapoint(self, i):
        """
        对第 i 个样本：预测 → 后处理 → 算 |猜-真| → 选颜色 → 截断标题。

        供 ThreadPoolExecutor.map 并行调用；返回元组便于主线程收集。
        """
        datapoint = self.data[i]
        value = self.predictor(datapoint)
        guess = self.post_process(value)
        truth = datapoint.price
        error = abs(guess - truth)
        color = self.color_for(error, truth)
        title = datapoint.title if len(datapoint.title) <= 40 else datapoint.title[:40] + "..."
        return title, guess, truth, error, color

    def chart(self, title):
        """
        散点图：横轴真实价、纵轴预测价。

        完美预测应落在 y=x 对角线上；偏离越大误差越大。
        颜色来自 color_for，帮助快速找到「估飞」的商品。
        """
        df = pd.DataFrame(
            {
                "truth": self.truths,
                "guess": self.guesses,
                "title": self.titles,
                "error": self.errors,
                "color": self.colors,
            }
        )

        # Pre-format hover text：鼠标悬停显示商品名与价格对比
        df["hover"] = [
            f"{t}\nGuess=${g:,.2f} Actual=${y:,.2f}"
            for t, g, y in zip(df["title"], df["guess"], df["truth"])
        ]

        max_val = float(max(df["truth"].max(), df["guess"].max()))

        fig = px.scatter(
            df,
            x="truth",
            y="guess",
            color="color",
            color_discrete_map={"green": "green", "orange": "orange", "red": "red"},
            title=title,
            labels={"truth": "Actual Price", "guess": "Predicted Price"},
            width=1000,
            height=800,
        )

        # Assign customdata per trace (one color/category = one trace)
        for tr in fig.data:
            mask = df["color"] == tr.name
            tr.customdata = df.loc[mask, ["hover"]].to_numpy()
            tr.hovertemplate = "%{customdata[0]}<extra></extra>"
            tr.marker.update(size=6)

        # Reference line y=x：理想预测参考线
        fig.add_trace(
            go.Scatter(
                x=[0, max_val],
                y=[0, max_val],
                mode="lines",
                line=dict(width=2, dash="dash", color="deepskyblue"),
                name="y = x",
                hoverinfo="skip",
                showlegend=False,
            )
        )

        fig.update_xaxes(range=[0, max_val])
        fig.update_yaxes(range=[0, max_val])
        fig.update_layout(showlegend=False)
        fig.show()

    def error_trend_chart(self):
        """
        累计平均绝对误差曲线 + 95% 置信区间。

        随评估样本增多，均值是否收敛？若波动很大，说明 size 可能不够稳。
        灰色带 ≈ 对当前累计均值不确定度的直观提示（近似 1.96 × 标准误）。
        """
        n = len(self.errors)

        # Running mean and std (pure Python)
        running_sums = list(accumulate(self.errors))
        x = list(range(1, n + 1))
        running_means = [s / i for s, i in zip(running_sums, x)]

        running_squares = list(accumulate(e * e for e in self.errors))
        running_stds = [
            math.sqrt((sq_sum / i) - (mean**2)) if i > 1 else 0
            for i, sq_sum, mean in zip(x, running_squares, running_means)
        ]

        # 95% confidence interval for mean：约 1.96 * 标准误
        ci = [1.96 * (sd / math.sqrt(i)) if i > 1 else 0 for i, sd in zip(x, running_stds)]
        upper = [m + c for m, c in zip(running_means, ci)]
        lower = [m - c for m, c in zip(running_means, ci)]

        # Plot
        fig = go.Figure()

        # Shaded confidence interval band
        fig.add_trace(
            go.Scatter(
                x=x + x[::-1],
                y=upper + lower[::-1],
                fill="toself",
                fillcolor="rgba(128,128,128,0.2)",
                line=dict(color="rgba(255,255,255,0)"),
                hoverinfo="skip",
                showlegend=False,
                name="95% CI",
            )
        )

        # Main line with hover text showing CI
        fig.add_trace(
            go.Scatter(
                x=x,
                y=running_means,
                mode="lines",
                line=dict(width=3, color="firebrick"),
                name="Cumulative Avg Error",
                customdata=list(
                    zip(
                        ci,
                    )
                ),
                hovertemplate=(
                    "n=%{x}<br>"
                    "Avg Error=$%{y:,.2f}<br>"
                    "±95% CI=$%{customdata[0]:,.2f}<extra></extra>"
                ),
            )
        )

        # Title with final stats
        final_mean = running_means[-1]
        final_ci = ci[-1]
        title = f"{self.title} Error: ${final_mean:,.2f} ± ${final_ci:,.2f}"

        fig.update_layout(
            title=title,
            xaxis_title="Number of Datapoints",
            yaxis_title="Average Absolute Error ($)",
            width=1000,
            height=360,
            template="plotly_white",
            showlegend=False,
        )

        fig.show()

    def report(self):
        """汇总 MAE / MSE / R²，并画出误差趋势与散点图。"""
        average_error = sum(self.errors) / self.size
        mse = mean_squared_error(self.truths, self.guesses)
        r2 = r2_score(self.truths, self.guesses) * 100
        title = f"{self.title} results<br><b>Error:</b> ${average_error:,.2f} <b>MSE:</b> {mse:,.0f} <b>r²:</b> {r2:.1f}%"
        self.error_trend_chart()
        self.chart(title)

    def run(self):
        """用线程池并行评估 size 个点，边跑边打印彩色误差，最后出报告。"""
        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            for title, guess, truth, error, color in tqdm(
                ex.map(self.run_datapoint, range(self.size)), total=self.size
            ):
                self.titles.append(title)
                self.guesses.append(guess)
                self.truths.append(truth)
                self.errors.append(error)
                self.colors.append(color)
                print(f"{COLOR_MAP[color]}${error:.0f} ", end="")
        self.report()


def evaluate(function, data, size=DEFAULT_SIZE, workers=WORKERS):
    """便捷入口：构造 Tester 并立即 run()。notebook 里一行即可出完整评估面板。"""
    Tester(function, data, size=size, workers=workers).run()
