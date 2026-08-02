from typing import Optional, List
from agents.agent import Agent
from agents.deals import Deal, Opportunity
from agents.scanner_agent import ScannerAgent
from agents.ensemble_agent import EnsembleAgent
from agents.messaging_agent import MessagingAgent


class PlanningAgent(Agent):
    name = "Planning Agent"
    color = Agent.GREEN
    DEAL_THRESHOLD = 5

    def __init__(self, collection):
        """创建该规划器协调的 3 个代理的实例"""
        self.log("Planning Agent is initializing")
        self.scanner = ScannerAgent()
        self.ensemble = EnsembleAgent(collection)
        self.messenger = MessagingAgent()
        self.log("Planning Agent is ready")

    def run(self, deal: Deal) -> Opportunity:
        """运行特定交易的工作流程
        :param deal: 交易，从 RSS 抓取中总结
        ：返回： 包含折扣的机会"""
        self.log("Planning Agent is pricing up a potential deal")
        estimate = self.ensemble.price(deal.product_description)
        discount = estimate - deal.price
        self.log(f"Planning Agent has processed a deal with discount ${discount:.2f}")
        return Opportunity(deal=deal, estimate=estimate, discount=discount)

    def plan(self, memory: List[str] = []) -> Optional[Opportunity]:
        """运行完整的工作流程：
        1. 使用 ScannerAgent 从 RSS 源中查找优惠
        2.使用EnsembleAgent来估计它们
        3. 使用MessagingAgent发送交易通知
        :param memory: 过去出现过的 URL 列表
        :return: 如果有机会出现，则为机会，否则为无"""
        self.log("Planning Agent is kicking off a run")
        selection = self.scanner.scan(memory=memory)
        if selection:
            opportunities = [self.run(deal) for deal in selection.deals[:5]]
            opportunities.sort(key=lambda opp: opp.discount, reverse=True)
            best = opportunities[0]
            self.log(
                f"Planning Agent has identified the best deal has discount ${best.discount:.2f}"
            )
            if best.discount > self.DEAL_THRESHOLD:
                self.messenger.alert(best)
            self.log("Planning Agent has completed a run")
            return best if best.discount > self.DEAL_THRESHOLD else None
        return None
