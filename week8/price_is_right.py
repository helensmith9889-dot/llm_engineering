"""
「The Price is Right」Gradio 前端：可视化多智能体自动扫货框架。

用户打开页面后会：
  1. 后台线程调用 DealAgentFramework.run()（Scanner→Ensemble→Messaging）
  2. 日志经 QueueHandler 流入队列，reformat 成彩色 HTML 实时刷新
  3. 表格展示已发现的 Opportunity（标价 / 估价 / 折扣 / URL）
  4. 右侧 3D 散点展示向量库商品分布（t-SNE 降维后的 embedding）
  5. Timer 每 300 秒再跑一轮；点击表格行可手动再推送一条 alert

为什么要用「线程 + 队列」而不是在 Gradio 回调里直接同步跑 Agent？
  一整轮扫货可能要几十秒（抓 RSS、多次 LLM/Modal 调用）。若阻塞 UI 线程，
  页面会假死；把重活丢到 worker 线程，主侧用生成器 yield 刷新日志，体验更像「直播」。

教学要点：把多 Agent 系统产品化——不仅有规划与估价，还有可观察的 UI 与记忆。
"""

import logging
import queue
import threading
import time
import gradio as gr
from deal_agent_framework import DealAgentFramework
from log_utils import reformat
import plotly.graph_objects as go
from dotenv import load_dotenv

load_dotenv(override=True)


class QueueHandler(logging.Handler):
    """
    自定义 logging Handler：把每条日志 format 后放入线程安全队列，供 UI 轮询。

    标准库 logging 默认打到控制台；这里改成「打进 queue.Queue」，
    这样 Gradio 一侧可以非阻塞地 get_nowait 取新日志并渲染。
    """

    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        """logging 回调：格式化 record 并 put 进队列（在打日志的线程里执行）。"""
        self.log_queue.put(self.format(record))


def html_for(log_data):
    """
    把最近约 18 条日志拼成可滚动的深色 HTML 面板。

    只保留末尾若干条，避免 DOM 无限变长拖慢浏览器。

    参数:
        log_data: 已 reformat 的 HTML 片段列表
    """
    output = "<br>".join(log_data[-18:])
    return f"""
    <div id="scrollContent" style="height: 400px; overflow-y: auto; border: 1px solid #ccc; background-color: #222229; padding: 10px;">
    {output}
    </div>
    """


def setup_logging(log_queue):
    """给根 logger 挂上 QueueHandler，统一时间格式。"""
    handler = QueueHandler(log_queue)
    formatter = logging.Formatter(
        "[%(asctime)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S %z",
    )
    handler.setFormatter(formatter)
    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class App:
    """Gradio 应用外壳：持有 DealAgentFramework 单例并构建 Blocks UI。"""

    def __init__(self):
        # 懒加载：打开页面瞬间不必立刻连向量库 / 初始化全部 Agent
        self.agent_framework = None

    def get_agent_framework(self):
        """懒创建框架实例（首次需要时再连向量库 / 初始化 Planning）。"""
        if not self.agent_framework:
            self.agent_framework = DealAgentFramework()
        return self.agent_framework

    def run(self):
        """构建 Gradio Blocks：表格 + 日志 + 3D 图 + 定时自动跑 agent。"""
        with gr.Blocks(title="The Price is Right", fill_width=True) as ui:
            # gr.State：跨回调持久保存的 Python 对象（这里是日志 HTML 片段列表）
            log_data = gr.State([])

            def table_for(opps):
                """把 Opportunity 列表转成 Dataframe 行：描述、价格、估价、折扣、URL。"""
                return [
                    [
                        opp.deal.product_description,
                        f"${opp.deal.price:.2f}",
                        f"${opp.estimate:.2f}",
                        f"${opp.discount:.2f}",
                        opp.deal.url,
                    ]
                    for opp in opps
                ]

            def update_output(log_data, log_queue, result_queue):
                """
                生成器：持续从日志队列取消息刷新 UI；拿到 worker 最终表格后结束。

                用 yield 实现 Gradio 流式更新，避免长时间卡住界面。
                模式：有日志就刷；有最终 result 就记下；两者都空则短暂 sleep 再轮询。
                """
                initial_result = table_for(self.get_agent_framework().memory)
                final_result = None
                while True:
                    try:
                        message = log_queue.get_nowait()
                        log_data.append(reformat(message))
                        yield log_data, html_for(log_data), final_result or initial_result
                    except queue.Empty:
                        try:
                            final_result = result_queue.get_nowait()
                            yield log_data, html_for(log_data), final_result or initial_result
                        except queue.Empty:
                            # 已经拿到最终表格且暂时没有新日志 → 结束生成器
                            if final_result is not None:
                                break
                            time.sleep(0.1)

            def get_initial_plot():
                """占位图：向量库尚未加载完时显示 Loading。"""
                fig = go.Figure()
                fig.update_layout(
                    title="Loading vector DB...",
                    height=400,
                )
                return fig

            def get_plot():
                """
                从框架取 t-SNE 三维坐标，画商品 embedding 散点图。

                embedding 本身可能是上千维；t-SNE 把它压到 3D 仅供「肉眼看分布」，
                不是给模型检索用的坐标。颜色通常编码品类或其它标签。
                """
                documents, vectors, colors = DealAgentFramework.get_plot_data(max_datapoints=800)
                # Create the 3D scatter plot
                fig = go.Figure(
                    data=[
                        go.Scatter3d(
                            x=vectors[:, 0],
                            y=vectors[:, 1],
                            z=vectors[:, 2],
                            mode="markers",
                            marker=dict(size=2, color=colors, opacity=0.7),
                        )
                    ]
                )

                fig.update_layout(
                    scene=dict(
                        xaxis_title="x",
                        yaxis_title="y",
                        zaxis_title="z",
                        aspectmode="manual",
                        aspectratio=dict(x=2.2, y=2.2, z=1),  # Make x-axis twice as long
                        camera=dict(
                            eye=dict(x=1.6, y=1.6, z=0.8)  # Adjust camera position
                        ),
                    ),
                    height=400,
                    margin=dict(r=5, b=1, l=5, t=2),
                )

                return fig

            def do_run():
                """同步执行一轮框架 run()，返回更新后的表格数据。"""
                new_opportunities = self.get_agent_framework().run()
                table = table_for(new_opportunities)
                return table

            def run_with_logging(initial_log_data):
                """
                在后台线程跑 do_run，主协程用 update_output 推送日志与最终表格。

                log_queue：worker 侧 logging → UI
                result_queue：worker 跑完后的 Dataframe 行 → UI
                """
                log_queue = queue.Queue()
                result_queue = queue.Queue()
                setup_logging(log_queue)

                def worker():
                    result = do_run()
                    result_queue.put(result)

                thread = threading.Thread(target=worker)
                thread.start()

                for log_data, output, final_result in update_output(
                    initial_log_data, log_queue, result_queue
                ):
                    yield log_data, output, final_result

            def do_select(selected_index: gr.SelectData):
                """用户点击表格某一行时，对该 Opportunity 再发一次 Messaging alert。"""
                opportunities = self.get_agent_framework().memory
                row = selected_index.index[0]
                opportunity = opportunities[row]
                self.get_agent_framework().planner.messenger.alert(opportunity)

            with gr.Row():
                gr.Markdown(
                    '<div style="text-align: center;font-size:24px"><strong>The Price is Right</strong> - Autonomous Agent Framework that hunts for deals</div>'
                )
            with gr.Row():
                gr.Markdown(
                    '<div style="text-align: center;font-size:14px">A proprietary fine-tuned LLM deployed on Modal and a RAG pipeline with a frontier model collaborate to send push notifications with great online deals.</div>'
                )
            with gr.Row():
                opportunities_dataframe = gr.Dataframe(
                    headers=["Deals found so far", "Price", "Estimate", "Discount", "URL"],
                    wrap=True,
                    column_widths=[6, 1, 1, 1, 3],
                    row_count=10,
                    col_count=5,
                    max_height=400,
                )
            with gr.Row():
                with gr.Column(scale=1):
                    logs = gr.HTML()
                with gr.Column(scale=1):
                    plot = gr.Plot(value=get_plot(), show_label=False)

            # 页面加载时立即跑一轮带日志的 agent
            ui.load(
                run_with_logging,
                inputs=[log_data],
                outputs=[log_data, logs, opportunities_dataframe],
            )

            # 每 300 秒自动再扫一轮（持续猎优惠）
            timer = gr.Timer(value=300, active=True)
            timer.tick(
                run_with_logging,
                inputs=[log_data],
                outputs=[log_data, logs, opportunities_dataframe],
            )

            # 点击表格行 → 手动再推送该条机会
            opportunities_dataframe.select(do_select)

        ui.launch(share=False, inbrowser=True)


if __name__ == "__main__":
    App().run()
