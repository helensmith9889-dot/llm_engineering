import modal
from agents.agent import Agent


class SpecialistAgent(Agent):
    """运行我们微调的 LLM 的代理，该代理在 Modal 上远程运行"""

    name = "Specialist Agent"
    color = Agent.RED

    def __init__(self):
        """通过创建模态类的实例来设置此代理"""
        self.log("Specialist Agent is initializing - connecting to modal")
        Pricer = modal.Cls.from_name("pricer-service", "Pricer")
        self.pricer = Pricer()

    def price(self, description: str) -> float:
        """进行远程调用以返回该商品的预估价格"""
        self.log("Specialist Agent is calling remote fine-tuned model")
        result = self.pricer.price.remote(description)
        self.log(f"Specialist Agent completed - predicting ${result:.2f}")
        return result
