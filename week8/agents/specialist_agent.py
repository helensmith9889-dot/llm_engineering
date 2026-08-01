"""
Specialist Agent（专家定价 Agent）：调用部署在 Modal 上的微调 LLM 做估价。

在多智能体扫货系统中，本 Agent 是 Ensemble 的一票：
  它不自己加载大模型，而是通过 Modal 的远程类调用 pricer-service 里的 Pricer.price。

教学要点：
  - Fine-tuned LLM（微调大模型）：在定价数据上继续训练，比通用聊天更懂「报价」
  - Modal：用代码定义云端 GPU 服务；本地只发 description，远端返回 float 价格
  - 与 Frontier（RAG+前沿模型）、NeuralNetwork（DNN）形成 Ensemble

对应服务代码见 week8/pricer_service2.py（Pricer 类）。
"""

import modal
from agents.agent import Agent


class SpecialistAgent(Agent):
    """
    An Agent that runs our fine-tuned LLM that's running remotely on Modal

    （中文补充）连接 Modal 上名为 pricer-service 的远程定价服务，
    对商品描述调用微调模型，返回估计价格。
    """

    name = "Specialist Agent"
    color = Agent.RED

    def __init__(self):
        """
        初始化：从 Modal 按名称查找远程类 Pricer，并创建可调用实例。

        modal.Cls.from_name("pricer-service", "Pricer") 表示：
          - App 名：pricer-service
          - 类名：Pricer
        需先用 modal deploy 把服务部署好，本地才能连上。
        """
        self.log("Specialist Agent is initializing - connecting to modal")
        Pricer = modal.Cls.from_name("pricer-service", "Pricer")
        self.pricer = Pricer()

    def price(self, description: str) -> float:
        """
        远程调用微调模型，估计商品价格。

        参数:
            description: 商品描述（通常已经过 Preprocessor 改写）

        返回:
            估计价格（美元）。.remote(...) 表示在 Modal 容器里执行，本地等待结果。
        """
        self.log("Specialist Agent is calling remote fine-tuned model")
        result = self.pricer.price.remote(description)
        self.log(f"Specialist Agent completed - predicting ${result:.2f}")
        return result
