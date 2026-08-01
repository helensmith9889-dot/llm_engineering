"""
Neural Network Agent（神经网络定价 Agent）：用本地深度网络估计商品价格。

在 Ensemble 三人组中，本 Agent 代表「传统深度学习」路线：
  文本 → HashingVectorizer 特征 → DeepNeuralNetwork → 美元价格

与 Specialist（云端微调 LLM）、Frontier（RAG + 前沿 LLM）互补，
共同组成加权集成，降低单一模型失误带来的「假捡漏」。

权重文件：deep_neural_network.pth（需事先训练并放在运行目录）。
"""

from agents.agent import Agent
from agents.deep_neural_network import DeepNeuralNetworkInference


class NeuralNetworkAgent(Agent):
    """
    包装 DeepNeuralNetworkInference 的 Agent，提供与其它定价 Agent 一致的 price() 接口。
    """

    name = "Neural Network Agent"
    color = Agent.MAGENTA

    def __init__(self):
        """
        Initialize this object by loading in the saved model weights
        and the SentenceTransformer vector encoding model

        （中文补充）实际加载的是 HashingVectorizer + PyTorch DNN 权重；
        docstring 里提到的 SentenceTransformer 是历史表述，以 deep_neural_network.py 为准。
        """
        self.log("Neural Network Agent is initializing")
        self.neural_network = DeepNeuralNetworkInference()
        self.neural_network.setup()
        # 从磁盘加载训练好的 state_dict
        self.neural_network.load("deep_neural_network.pth")
        self.log("Neural Network Agent is ready and weights are loaded")

    def price(self, description: str) -> float:
        """
        Use the Deep Neural Network to estimate the price of the described item

        参数:
            description: 待估价的商品描述文本
        返回:
            估计价格（浮点数，美元）；内部会做 log 空间反变换与非负截断。
        """
        self.log("Neural Network Agent is starting a prediction")
        result = self.neural_network.inference(description)
        self.log(f"Neural Network Agent completed - predicting ${result:.2f}")
        return result
