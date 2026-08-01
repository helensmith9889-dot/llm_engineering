"""
Ensemble Agent（集成定价 Agent）：把多个定价模型的结果加权合成最终估价。

在「Price is Right」多智能体系统里，估价是核心能力——标价低于「真价」才叫捡漏。
单一模型难免偏差，因此采用 Ensemble（集成学习）思路：

  Preprocessor 改写描述
       ↓
  ┌────┴────┬────────────────┐
  Specialist  Frontier      NeuralNetwork
  (微调 LLM)  (RAG+前沿模型)  (深度神经网络)
       ↓         ↓               ↓
       └────加权平均（0.1 / 0.8 / 0.1）────┘
                    ↓
              最终 estimate

本 Agent 被 PlanningAgent / AutonomousPlanningAgent 调用，不直接发通知。
"""

from agents.agent import Agent
from agents.specialist_agent import SpecialistAgent
from agents.frontier_agent import FrontierAgent
from agents.neural_network_agent import NeuralNetworkAgent
from agents.preprocessor import Preprocessor


class EnsembleAgent(Agent):
    """
    集成定价 Agent：协调三个子模型 + 文本预处理器，输出一个加权价格。

    name / color 用于彩色日志，便于在框架总日志里追踪本 Agent。
    """

    name = "Ensemble Agent"
    color = Agent.YELLOW

    def __init__(self, collection):
        """
        创建 Ensemble：实例化各子 Agent，并准备好预处理器。

        参数:
            collection: Chroma 向量库 collection，传给 FrontierAgent 做 RAG 相似商品检索。

        说明：Specialist 会连 Modal 远程服务；NeuralNetwork 会加载本地 .pth 权重。
        """
        self.log("Initializing Ensemble Agent")
        self.specialist = SpecialistAgent()
        self.frontier = FrontierAgent(collection)
        self.neural_network = NeuralNetworkAgent()
        self.preprocessor = Preprocessor()
        self.log("Ensemble Agent is ready")

    def price(self, description: str) -> float:
        """
        运行完整集成定价流水线。

        步骤：
          1. Preprocessor 把杂乱描述改写成统一格式（Title/Category/Brand/...）
          2. 三个子模型各自给出估价
          3. 线性加权：Frontier 0.8 + Specialist 0.1 + NeuralNetwork 0.1
             （权重可理解为「谁更可信」；本课中 RAG+大模型占主导）

        参数:
            description: 商品描述文本（通常来自 Deal.product_description）

        返回:
            加权后的价格估计（浮点数，单位美元）
        """
        self.log("Running Ensemble Agent - preprocessing text")
        rewrite = self.preprocessor.preprocess(description)
        self.log(f"Pre-processed text using {self.preprocessor.model_name}")
        specialist = self.specialist.price(rewrite)
        frontier = self.frontier.price(rewrite)
        neural_network = self.neural_network.price(rewrite)
        # 加权集成：不是简单平均，而是按经验/验证集表现分配权重
        combined = frontier * 0.8 + specialist * 0.1 + neural_network * 0.1
        self.log(f"Ensemble Agent complete - returning ${combined:.2f}")
        return combined
