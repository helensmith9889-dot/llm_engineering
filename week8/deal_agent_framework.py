"""
Deal Agent Framework：多智能体「Price is Right」扫货系统的总调度框架。

职责概览：
  1. 连接 Chroma 持久化向量库（products_vectorstore）——给 Frontier/Ensemble 做 RAG
  2. 读写 memory.json——记住已发现的 Opportunity，避免重复推送
  3. 懒加载 PlanningAgent，执行一轮 plan()，并把新机会追加进记忆
  4. 提供 get_plot_data()：用 t-SNE 把商品向量降到 3D，供 Gradio UI 可视化

教学关键词：Orchestration（编排）、Memory（智能体记忆）、Vector DB、多 Agent 协作入口。
运行：python deal_agent_framework.py 会直接跑一轮。
"""

import os
import sys
import logging
import json
from typing import List
from dotenv import load_dotenv
import chromadb
from agents.planning_agent import PlanningAgent
from agents.deals import Opportunity
from sklearn.manifold import TSNE
import numpy as np

load_dotenv(override=True)

# Colors for logging：框架自身日志用蓝底白字，区别于各 Agent 的彩色前缀
BG_BLUE = "\033[44m"
WHITE = "\033[37m"
RESET = "\033[0m"

# Colors for plot：类别名 → 散点颜色（与向量库 metadata["category"] 对齐）
CATEGORIES = [
    "Appliances",
    "Automotive",
    "Cell_Phones_and_Accessories",
    "Electronics",
    "Musical_Instruments",
    "Office_Products",
    "Tools_and_Home_Improvement",
    "Toys_and_Games",
]
COLORS = ["red", "blue", "brown", "orange", "yellow", "green", "purple", "cyan"]


def init_logging():
    """
    配置根 logger：INFO 级别，输出到 stdout，带时间戳与 [Agents] 标签。
    """
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "[%(asctime)s] [Agents] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S %z",
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)


class DealAgentFramework:
    """
    扫货多智能体框架：向量库 + 记忆 + PlanningAgent。
    """

    DB = "products_vectorstore"
    MEMORY_FILENAME = "memory.json"

    def __init__(self):
        """初始化日志、Chroma collection、从磁盘加载 memory；planner 延迟创建。"""
        init_logging()
        client = chromadb.PersistentClient(path=self.DB)
        self.memory = self.read_memory()
        self.collection = client.get_or_create_collection("products")
        self.planner = None

    def init_agents_as_needed(self):
        """懒加载 PlanningAgent（及其内部 Scanner/Ensemble/Messaging），避免 import 时就连 Modal。"""
        if not self.planner:
            self.log("Initializing Agent Framework")
            self.planner = PlanningAgent(self.collection)
            self.log("Agent Framework is ready")

    def read_memory(self) -> List[Opportunity]:
        """从 memory.json 反序列化 Opportunity 列表；文件不存在则返回空列表。"""
        if os.path.exists(self.MEMORY_FILENAME):
            with open(self.MEMORY_FILENAME, "r") as file:
                data = json.load(file)
            opportunities = [Opportunity(**item) for item in data]
            return opportunities
        return []

    def write_memory(self) -> None:
        """把当前 memory 以缩进 JSON 写回磁盘。"""
        data = [opportunity.model_dump() for opportunity in self.memory]
        with open(self.MEMORY_FILENAME, "w") as file:
            json.dump(data, file, indent=2)

    @classmethod
    def reset_memory(cls) -> None:
        """
        调试用：若存在记忆文件，只保留前 2 条，便于重复测试扫描去重逻辑。
        """
        data = []
        if os.path.exists(cls.MEMORY_FILENAME):
            with open(cls.MEMORY_FILENAME, "r") as file:
                data = json.load(file)
        truncated = data[:2]
        with open(cls.MEMORY_FILENAME, "w") as file:
            json.dump(truncated, file, indent=2)

    def log(self, message: str):
        """框架级彩色日志（蓝底白字 + [Agent Framework] 前缀）。"""
        text = BG_BLUE + WHITE + "[Agent Framework] " + message + RESET
        logging.info(text)

    def run(self) -> List[Opportunity]:
        """
        跑一轮完整规划：必要时初始化 agents → plan(memory) → 有结果则追加并落盘。

        返回:
            更新后的完整 memory 列表（含历史机会）
        """
        self.init_agents_as_needed()
        logging.info("Kicking off Planning Agent")
        result = self.planner.plan(memory=self.memory)
        logging.info(f"Planning Agent has completed and returned: {result}")
        if result:
            self.memory.append(result)
            self.write_memory()
        return self.memory

    @classmethod
    def get_plot_data(cls, max_datapoints=2000):
        """
        从 Chroma 取出 embeddings，用 t-SNE 降到 3 维，供 UI 做 3D 散点图。

        参数:
            max_datapoints: 最多取多少条，避免 t-SNE 过慢
        返回:
            (documents, reduced_vectors, colors)
        """
        client = chromadb.PersistentClient(path=cls.DB)
        collection = client.get_or_create_collection("products")
        result = collection.get(
            include=["embeddings", "documents", "metadatas"], limit=max_datapoints
        )
        vectors = np.array(result["embeddings"])
        documents = result["documents"]
        categories = [metadata["category"] for metadata in result["metadatas"]]
        colors = [COLORS[CATEGORIES.index(c)] for c in categories]
        # t-SNE：把高维 embedding 压到 3D，保留局部邻近关系，便于肉眼看品类团簇
        tsne = TSNE(n_components=3, random_state=42, n_jobs=-1)
        reduced_vectors = tsne.fit_transform(vectors)
        return documents, reduced_vectors, colors


if __name__ == "__main__":
    DealAgentFramework().run()
