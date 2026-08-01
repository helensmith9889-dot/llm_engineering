"""
Week 7 评估工具：针对「prompt / completion」字典样本的定价器测试。

微调（fine-tuning）完成后，测试集常常已经变成 Hugging Face Dataset 的一行行字典：
  {"prompt": "……商品描述……", "completion": "199.00"}
其中 completion 就是「标准答案价格」（SFT 训练时的标签），不是 Item 对象上的 .price。

本模块的 Tester 做什么：
  1. 把你的预测函数 predictor 接到每一行数据上，得到「猜价」
  2. 从 completion 读出「真价」，从 prompt 里尽量解析 Title 方便看图
  3. 顺序评估（不用线程池——有些环境/模型不适合并行）
  4. 算 Error / MSE / R²，画散点图与累计误差曲线
  5. 结束时用 clear_output 清掉中间彩色打印，notebook 里只留最终图表

常见回归评估指标（给绝对初学者）：
  - Error / MAE（平均绝对误差）：|猜价 − 真价| 的平均，单位是美元，最好懂
  - MSE（均方误差）：把误差平方再平均——大错误会被放大，对「离谱猜价」更敏感
  - R²（决定系数）：模型解释了多少价格波动；1 最好，0 像瞎猜均值；这里 *100 显示成百分比风格

与 week7/pricer/evaluator.py 的差异：数据形态不同（dict vs Item 对象），且本文件默认顺序跑。
"""

import re
from sklearn.metrics import mean_squared_error, r2_score
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from itertools import accumulate
import math
from tqdm.auto import tqdm
from IPython.display import clear_output


# 终端 ANSI 颜色码：print 时给误差数字上色，绿=好、黄=中、红=差
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
COLOR_MAP = {"red": RED, "orange": YELLOW, "green": GREEN}

# 默认评估多少条样本（不必跑完整测试集，先看趋势即可）
DEFAULT_SIZE = 200


class Tester:
    """
    评估「吃 datapoint 字典、吐价格」的预测函数。

    真值来自 datapoint["completion"]（SFT 标签），不是 Item.price。
    适合 Week 7 notebook 里已经整理成 prompt/completion 的微调测试集。
    """

    def __init__(self, predictor, data, title=None, size=DEFAULT_SIZE):
        """
        参数:
            predictor: 接收一行 dict（含 prompt/completion），返回价格猜测（数字或字符串）
            data: 可索引的数据集（list 或 Hugging Face Dataset）
            title: 图表标题；默认从 predictor 函数名自动美化
            size: 评估条数（从索引 0 开始取前 size 条）
        """
        self.predictor = predictor
        self.data = data
        self.title = title or self.make_title(predictor)
        self.size = size
        # 下面五个列表一一对应：第 i 个样本的标题、猜价、真价、误差、颜色
        self.titles = []
        self.guesses = []
        self.truths = []
        self.errors = []
        self.colors = []

    @staticmethod
    def make_title(predictor) -> str:
        """函数名 → 人类可读标题（下划线变空格，并把 Gpt 规范成 GPT）。"""
        return predictor.__name__.replace("__", ".").replace("_", " ").title().replace("Gpt", "GPT")

    @staticmethod
    def post_process(value):
        """
        把模型输出统一成 float，方便算误差。

        微调/LLM 有时返回「$1,299」或夹杂文字；去掉 $ 与逗号后，用正则抓第一个数字。
        已经是数字则原样返回。抓不到数字时退回 0（避免整次评估崩溃）。
        """
        if isinstance(value, str):
            value = value.replace("$", "").replace(",", "")
            match = re.search(r"[-+]?\d*\.\d+|\d+", value)
            return float(match.group()) if match else 0
        else:
            return value

    def color_for(self, error, truth):
        """
        按绝对误差或相对误差映射绿 / 橙 / 红，便于终端一眼扫质量。

        规则是课程约定的启发式阈值（不是统计学唯一标准）：
          - 绿：误差 < $40，或相对误差 < 20%
          - 橙：误差 < $80，或相对误差 < 40%
          - 红：更差
        """
        if error < 40 or error / truth < 0.2:
            return "green"
        elif error < 80 or error / truth < 0.4:
            return "orange"
        else:
            return "red"

    def run_datapoint(self, i):
        """
        评估第 i 行：真值 = float(completion)；标题尽量从 prompt 里「Title:」后截取。

        摘要预处理格式若含 Title: 行，图表悬停时能显示商品名而不是整段 prompt。
        返回 (title, guess, truth, error, color)，供 run() 收集进列表。
        """
        datapoint = self.data[i]
        value = self.predictor(datapoint)
        guess = self.post_process(value)
        # completion 在 SFT 数据里通常是价格字符串，例如 "199.00"
        truth = float(datapoint["completion"])
        error = abs(guess - truth)
        color = self.color_for(error, truth)
        # 尝试从 prompt 解析 Title；没有则退回整段开头
        pieces = datapoint["prompt"].split("Title: ")
        title = pieces[1].split("\n")[0] if len(pieces) > 1 else pieces[0]
        title = title if len(title) <= 40 else title[:40] + "..."
        return title, guess, truth, error, color

    def chart(self, title):
        """
        真实价 vs 预测价散点图。

        读图技巧：点越靠近对角线 y=x，定价越准；
        点在线上方 = 猜贵了，线下方 = 猜便宜了。颜色对应 color_for 的好坏。
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

        # Pre-format hover text：鼠标悬停显示商品名与猜价/真价对比
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
            width=800,
            height=600,
        )

        # Assign customdata per trace (one color/category = one trace)
        # Plotly 按颜色分成多条 trace，必须分别挂上对应行的 hover 文本
        for tr in fig.data:
            mask = df["color"] == tr.name
            tr.customdata = df.loc[mask, ["hover"]].to_numpy()
            tr.hovertemplate = "%{customdata[0]}<extra></extra>"
            tr.marker.update(size=6)

        # Reference line y=x：完美预测应落在这条虚线上
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
        累计平均绝对误差与 95% 置信带（与 week6 评估器同思路）。

        为什么画「随 n 变化」而不只报一个最终平均数？
          - 看误差是否随样本增多而稳定（收敛）
          - 灰色带宽 ≈ 对「当前均值有多不确定」的直观提示
        95% CI 这里用常见近似：1.96 × (标准差 / √n)，n=1 时没有标准差故为 0。
        """
        n = len(self.errors)

        # Running mean and std (pure Python)：前缀和 → 第 i 步的累计均值
        running_sums = list(accumulate(self.errors))
        x = list(range(1, n + 1))
        running_means = [s / i for s, i in zip(running_sums, x)]

        # 用 E[X²] − (E[X])² 算运行标准差，避免每一步重新扫一遍列表
        running_squares = list(accumulate(e * e for e in self.errors))
        running_stds = [
            math.sqrt((sq_sum / i) - (mean**2)) if i > 1 else 0
            for i, sq_sum, mean in zip(x, running_squares, running_means)
        ]

        # 95% confidence interval for mean
        ci = [1.96 * (sd / math.sqrt(i)) if i > 1 else 0 for i, sd in zip(x, running_stds)]
        upper = [m + c for m, c in zip(running_means, ci)]
        lower = [m - c for m, c in zip(running_means, ci)]

        # Title with final stats：标题直接写最终均值 ± 置信半宽
        final_mean = running_means[-1]
        final_ci = ci[-1]
        title = f"{self.title} Error: {final_mean:,.2f} ± {final_ci:,.2f}"

        # Plot
        fig = go.Figure()

        # Shaded confidence interval band：用「上界正向 + 下界反向」围成填充多边形
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

        fig.update_layout(
            title=title,
            xaxis_title="Number of Datapoints",
            yaxis_title="Error ($)",
            width=800,
            height=300,
            template="plotly_white",
            showlegend=False,
        )

        fig.show()

    def report(self):
        """
        汇总 Error（平均绝对误差）/ MSE / R² 并展示两张图。

        R² 乘以 100 只是为了显示成「xx.x%」风格，便于和课程幻灯片对照；
        统计学教科书里的 R² 本身仍在 0–1（或可能为负）。
        """
        average_error = sum(self.errors) / self.size
        mse = mean_squared_error(self.truths, self.guesses)
        r2 = r2_score(self.truths, self.guesses) * 100
        title = f"{self.title} results<br><b>Error:</b> ${average_error:,.2f} <b>MSE:</b> {mse:,.0f} <b>r²:</b> {r2:.1f}%"
        self.error_trend_chart()
        self.chart(title)

    def run(self):
        """
        顺序评估 size 条；每条打印彩色误差；结束后 clear_output，只保留最终报告与图。

        clear_output 是 Jupyter 专用：清掉单元格里之前刷屏的 `$12 $45 ...`，
        避免 notebook 又长又乱，同时 wait=True 可减少闪烁。
        """
        for i in tqdm(range(self.size)):
            title, guess, truth, error, color = self.run_datapoint(i)
            self.titles.append(title)
            self.guesses.append(guess)
            self.truths.append(truth)
            self.errors.append(error)
            self.colors.append(color)
            print(f"{COLOR_MAP[color]}${error:.0f} ", end="")
        clear_output(wait=True)
        self.report()


def evaluate(function, data, size=DEFAULT_SIZE):
    """便捷入口：创建 Tester 并立刻 run()。notebook 里一行调用即可出图。"""
    Tester(function, data, size=size).run()
