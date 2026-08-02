from agents.agent import Agent
from agents.frontier_agent import FrontierAgent
from agents.preprocessor import Preprocessor
from agents.specialist_agent import SpecialistAgent


class EnsembleAgent(Agent):
    name = "Ensemble Agent"
    color = Agent.YELLOW

    def __init__(self, collection):
        """通过创建每个模型来创建 Ensemble 的实例
        并加载 Ensemble 的权重"""
        self.log("Initializing Ensemble Agent")
        self.specialist = SpecialistAgent()
        self.frontier = FrontierAgent(collection)
        self.preprocessor = Preprocessor()
        self.log("Ensemble Agent is ready")

    def price(self, description: str) -> float:
        """运行这个集成模型
        询问每个型号的产品定价
        然后使用线性回归模型返回加权价格
        :param description: 产品的描述
        :return: 预估价格"""
        self.log("Running Ensemble Agent - preprocessing text")
        rewrite = self.preprocessor.preprocess(description)
        self.log(f"Pre-processed text using {self.preprocessor.model_name}")
        specialist = self.specialist.price(rewrite)
        frontier = self.frontier.price(rewrite)
        combined = frontier * 0.8 + specialist * 0.2
        self.log(f"Ensemble Agent complete - returning ${combined:.2f}")
        return combined
