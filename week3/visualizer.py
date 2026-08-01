"""
token 预测可视化工具（教学用）

本模块帮助初学者「看见」大语言模型（LLM）在生成文本时，每一步选了哪个 token，
以及当时还有哪些备选、概率各是多少。

核心思路：
1. 用 OpenAI API 流式生成，并开启 logprobs，拿到每个 token 的对数概率；
2. 用 NetworkX 建一张有向图（主路径 + 左右备选分支）；
3. 用 Matplotlib 画成纵向流程图，便于课堂演示与自学。

概念提示（matplotlib / 绘图）：
- NetworkX 负责「图数据结构」（节点、边）；Matplotlib 负责「画出来」。
- 节点颜色区分角色：起点 / 主路径 token / 备选 / 终点。
- 纵向布局让生成顺序从上到下阅读，更符合「一步一步生成」的直觉。
"""

import networkx as nx
import matplotlib.pyplot as plt
from typing import List, Dict
import math
from openai import OpenAI
from dotenv import load_dotenv

# 从 .env 加载 OPENAI_API_KEY 等环境变量（override=True 表示覆盖已有同名变量）
load_dotenv(override=True)


class TokenPredictor:
    """
    逐 token 调用聊天模型，并记录每一步的预测概率与备选项。

    概念提示：
    - LLM 生成是「自回归」：已生成的内容会作为下一步的上下文。
    - logprobs（对数概率）便于数值稳定；展示给人类时通常用 math.exp 转回普通概率（0~1）。
    - temperature=0 + 固定 seed，尽量让结果可复现，方便画图对比。

    属性:
        client: OpenAI 客户端实例。
        messages: 预留的消息列表（本类当前主要用单轮 prompt）。
        predictions: 预留的预测缓存列表。
        model_name: 要调用的模型名称字符串。
    """

    def __init__(self, model_name: str):
        """
        初始化预测器。

        参数:
            model_name: 模型 ID（如 gpt-4o-mini），会原样传给 API。
        """
        self.client = OpenAI()
        self.messages = []
        self.predictions = []
        self.model_name = model_name

    def predict_tokens(self, prompt: str, max_tokens: int = 100) -> List[Dict]:
        """
        按 token 流式生成文本，并跟踪每一步的预测概率。

        返回一个列表；每个元素描述「这一步实际采用的 token」及其概率，
        以及当时排名靠前的备选 token。

        参数:
            prompt: 用户提示词（将作为 role=user 的消息发送）。
            max_tokens: 最多生成多少个新 token，防止过长拖垮可视化。

        返回:
            List[Dict]，每个字典大致形如：
            {
                "token": 实际输出的 token 字符串,
                "probability": 该 token 的概率（0~1，已从 logprob 还原）,
                "alternatives": [(备选token, 概率), ...] 最多 2 个
            }

        概念提示：
        - stream=True：边生成边返回，适合「逐步」收集 logprobs。
        - top_logprobs=3：每个位置额外返回前 3 名候选（含最终选中的那个）。
        - logprob 是对数概率；概率 = exp(logprob)。数值越小（越负）表示越不可能。
        """
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0,  # Use temperature 0 for deterministic output
            logprobs=True,
            seed=42,
            top_logprobs=3,  # Get top 3 token predictions
            stream=True,  # Stream the response
        )

        predictions = []
        # 流式响应：每个 chunk 通常对应一小段增量（此处按单 token 内容处理）
        for chunk in response:
            # delta.content 有值才说明本 chunk 带来了可见文本增量
            if chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                # top_logprobs：当前步排名靠前的候选 token 及其 logprob
                logprobs = chunk.choices[0].logprobs.content[0].top_logprobs
                logprob_dict = {item.token: item.logprob for item in logprobs}

                # Get top predicted token and probability
                top_token = token
                top_prob = logprob_dict[token]

                # Get alternative predictions
                alternatives = []
                for alt_token, alt_prob in logprob_dict.items():
                    if alt_token != token:
                        # math.exp：把对数概率还原成普通概率，便于图上显示百分比
                        alternatives.append((alt_token, math.exp(alt_prob)))
                # 按概率从高到低排，后面只保留前两名备选
                alternatives.sort(key=lambda x: x[1], reverse=True)

                prediction = {
                    "token": top_token,
                    "probability": math.exp(top_prob),
                    "alternatives": alternatives[:2],  # Keep top 2 alternatives
                }
                predictions.append(prediction)

        return predictions


def create_token_graph(model_name: str, predictions: List[Dict]) -> nx.DiGraph:
    """
    根据预测结果构建有向图（DiGraph），展示主路径与备选分支。

    图结构示意：
        START → t0 → t1 → ... → END
                  ↘ alt   ↘ alt
        （备选节点挂在「前一个主节点」上，表示「当时差点选了谁」）

    参数:
        model_name: 写在 START 节点上的模型名标签（仅用于展示）。
        predictions: predict_tokens() 返回的预测列表。

    返回:
        nx.DiGraph：节点带 token / prob / color / size 等属性，供绘图函数读取。

    概念提示（NetworkX）：
    - DiGraph = 有向图，边有方向，适合表示「生成顺序」。
    - 节点属性（color、size）是自定义的，NetworkX 不强制，画图时再取出来用。
    """
    G = nx.DiGraph()

    # 起点：浅绿色，略小一点，标签里放模型名
    G.add_node("START", token=model_name, prob="START", color="lightgreen", size=4000)

    # First, create all main token nodes in sequence
    for i, pred in enumerate(predictions):
        token_id = f"t{i}"
        G.add_node(
            token_id,
            token=pred["token"],
            # 概率转成百分比字符串，保留 1 位小数，便于节点标签显示
            prob=f"{pred['probability'] * 100:.1f}%",
            color="lightblue",
            size=6000,
        )

        # 第一条边从 START 出发；之后串成 t0→t1→t2…
        if i == 0:
            G.add_edge("START", token_id)
        else:
            G.add_edge(f"t{i - 1}", token_id)

    # Then add alternative nodes with a different y-position
    last_id = None
    for i, pred in enumerate(predictions):
        # 备选边的「父节点」：第一步挂在 START，之后挂在前一个主 token
        parent_token = "START" if i == 0 else f"t{i - 1}"

        # Add alternative token nodes slightly below main sequence
        for j, (alt_token, alt_prob) in enumerate(pred["alternatives"]):
            alt_id = f"t{i}_alt{j}"
            G.add_node(
                alt_id, token=alt_token, prob=f"{alt_prob * 100:.1f}%", color="lightgray", size=6000
            )

            # Add edge from main token to its alternatives only
            G.add_edge(parent_token, alt_id)
            last_id = parent_token

    # 终点：红色；边从最后一个「父节点」连到 END（若无预测，last_id 可能为 None）
    G.add_node("END", token="END", prob="100%", color="red", size=6000)
    G.add_edge(last_id, "END")

    return G


def visualize_predictions(G: nx.DiGraph, figsize=(14, 80)):
    """
    用 Matplotlib 把 token 预测图画成纵向布局：主路径居中，备选分列左右。

    参数:
        G: create_token_graph() 生成的有向图。
        figsize: 画布宽高（英寸）。默认很高（80），因为 token 链往往很长，
                 纵向需要足够空间，否则节点会挤在一起。

    返回:
        matplotlib.pyplot 模块对象（已画好当前 figure），便于在 Notebook 中显示或保存。

    概念提示（matplotlib / plotting）：
    - figsize=(宽, 高)：单位是英寸；本地跑 LLM 可视化时，高大于宽很常见。
    - pos 字典：{节点id: (x, y)}，NetworkX 画图时按这个坐标放置节点。
    - axis("off")：关掉坐标轴，流程图看起来更干净。
    - xlim / ylim + margin：手动留白，避免节点贴边被裁切。
    """
    plt.figure(figsize=figsize)

    # Create custom positioning for nodes
    pos = {}
    spacing_y = 5  # Vertical spacing between main tokens
    spacing_x = 5  # Horizontal spacing for alternatives

    # Position main token nodes in a vertical line
    # 主节点：id 里不含 "_alt"；从上往下排，y 取负值所以越往后越靠下
    main_nodes = [n for n in G.nodes() if "_alt" not in n]
    for i, node in enumerate(main_nodes):
        pos[node] = (0, -i * spacing_y)  # Center main tokens vertically

    # Position alternative nodes to left and right of main tokens
    for node in G.nodes():
        if "_alt" in node:
            # 节点 id 形如 "t3_alt0"：拆出主 token 名与备选序号
            main_token = node.split("_")[0]
            alt_num = int(node.split("_alt")[1])
            if main_token in pos:
                # Place first alternative to left, second to right
                x_offset = -spacing_x if alt_num == 0 else spacing_x
                # y 与对应主节点几乎齐平，略加 0.05 做视觉微调
                pos[node] = (x_offset, pos[main_token][1] + 0.05)

    # Draw nodes
    # 颜色与尺寸来自建图时写入的节点属性
    node_colors = [G.nodes[node]["color"] for node in G.nodes()]
    node_sizes = [G.nodes[node]["size"] for node in G.nodes()]
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes)

    # Draw all edges as straight lines
    # arrows=True 显示箭头，体现「从父节点指向子节点」的生成方向
    nx.draw_networkx_edges(G, pos, edge_color="gray", arrows=True, arrowsize=20, alpha=0.7)

    # Add labels with token and probability
    # 标签两行：上行 token 文本，下行概率百分比
    labels = {node: f"{G.nodes[node]['token']}\n{G.nodes[node]['prob']}" for node in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels, font_size=14)

    plt.title("Token prediction.")
    plt.axis("off")

    # Adjust plot limits to ensure all nodes are visible
    margin = 8
    x_values = [x for x, y in pos.values()]
    y_values = [y for x, y in pos.values()]
    plt.xlim(min(x_values) - margin, max(x_values) + margin)
    plt.ylim(min(y_values) - margin, max(y_values) + margin)

    # plt.tight_layout()
    return plt
