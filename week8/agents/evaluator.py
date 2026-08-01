"""
定价模型评估工具：并行跑预测、算误差、画散点图与误差收敛曲线。

虽放在 agents/ 下，本模块更偏「实验评估」：在开发 Ensemble / Frontier / DNN
时用它快速对比「猜价 vs 真价」。扫货线上流水线（Planning）通常不直接调用这里。

给初学者的指标速记：
  - Error / MAE：平均 |猜价 − 真价|，单位美元，最好懂
  - MSE（均方误差）：误差平方再平均——离谱大错会被放大惩罚
  - R²（决定系数）：相对「瞎猜均值」好多少；这里 *100 显示成百分比风格
  - 绝对误差着色：绿/橙/红，直观看「哪些商品估飞了」
  - ThreadPoolExecutor：多线程加速 I/O 或 API 型 predictor（等网络时可重叠等待）
  - 95% CI 误差带：累计均值旁的不确定度示意，样本少时通常更宽
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

# 终端彩色打印误差时用的 ANSI 码
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
COLOR_MAP = {"red": RED, "orange": YELLOW, "green": GREEN}

WORKERS = 5
DEFAULT_SIZE = 200


class Tester:
    """
    对任意 predictor(datapoint)→价格 的可调用对象做批量测试与可视化。

    data[i] 需要有 .price（真值）与 .title（图表标签）。
    """

    def __init__(self, predictor, data, title=None, size=DEFAULT_SIZE, workers=WORKERS):
        """
        参数:
            predictor: 接受一条数据、返回价格（或含价格的字符串）的函数
            data: 可下标访问的数据集，元素需有 .price / .title
            title: 图表标题；默认从 predictor 函数名美化生成
            size: 评估前多少条样本
            workers: 线程池大小
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
        """从函数名生成更易读的标题（下划线转空格、GPT 大小写修正等）。"""
        return predictor.__name__.replace("__", ".").replace("_", " ").title().replace("Gpt", "GPT")

    @staticmethod
    def post_process(value):
        """
        把模型输出统一成 float：若是字符串则去掉 $、逗号并正则抠数字。

        Frontier/LLM 常返回带货币符号的文本；统一成数字后才能算 MAE/MSE。
        """
        if isinstance(value, str):
            value = value.replace("$", "").replace(",", "")
            match = re.search(r"[-+]?\d*\.\d+|\d+", value)
            return float(match.group()) if match else 0
        else:
            return value

    def color_for(self, error, truth):
        """
        根据绝对误差与相对误差给样本上色：绿（准）/ 橙（一般）/ 红（差）。

        阈值是课程经验值：既看「差了多少美元」，也看「相对真价偏了百分之几」。
        """
        if error < 40 or error / truth < 0.2:
            return "green"
        elif error < 80 or error / truth < 0.4:
            return "orange"
        else:
            return "red"

    def run_datapoint(self, i):
        """
        评估第 i 条数据：预测 → 算误差 → 定颜色 → 截断标题。

        此方法会被线程池并行调用，应尽量自包含。

        返回:
            (title, guess, truth, error, color) 元组，供并行 map 收集。
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
        画「真价 vs 预测价」散点图，并加上 y=x 参考线（完美预测应落在线上）。

        点在线上方 = 猜贵了；线下方 = 猜便宜了。
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

        # Pre-format hover text：鼠标悬停时显示商品名与价格对比
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

        # Reference line y=x
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
        画累计平均绝对误差随样本数 n 的变化，并带 95% 置信区间带。

        用途：看误差是否随评估进行而稳定，避免只看最终一个平均数。
        CI 近似：1.96 × (标准差 / √n)。
        """
        n = len(self.errors)

        # Running mean and std (pure Python)：用 accumulate 做前缀和，O(n) 算滑动均值
        running_sums = list(accumulate(self.errors))
        x = list(range(1, n + 1))
        running_means = [s / i for s, i in zip(running_sums, x)]

        running_squares = list(accumulate(e * e for e in self.errors))
        running_stds = [
            math.sqrt((sq_sum / i) - (mean**2)) if i > 1 else 0
            for i, sq_sum, mean in zip(x, running_squares, running_means)
        ]

        # 95% confidence interval for mean：近似用 1.96 * se
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
        """汇总平均绝对误差、MSE、R²，并依次展示误差趋势图与散点图。"""
        average_error = sum(self.errors) / self.size
        mse = mean_squared_error(self.truths, self.guesses)
        r2 = r2_score(self.truths, self.guesses) * 100
        title = f"{self.title} results<br><b>Error:</b> ${average_error:,.2f} <b>MSE:</b> {mse:,.0f} <b>r²:</b> {r2:.1f}%"
        self.error_trend_chart()
        self.chart(title)

    def run(self):
        """
        用线程池并行评估 size 条样本，边跑边彩色打印误差，最后 report()。

        map 保持与 range(size) 相同的结果顺序，便于列表与样本下标对齐。
        """
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
    """
    便捷入口：构造 Tester 并立即 run()。

    参数:
        function: 定价预测函数
        data: 带 price/title 的数据集
        size / workers: 样本量与并行度
    """
    Tester(function, data, size=size, workers=workers).run()
