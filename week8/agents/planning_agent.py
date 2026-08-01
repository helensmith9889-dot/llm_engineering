"""
Planning Agent（规划 Agent）：用固定工作流编排 Scanner → Ensemble → Messaging。

这是多智能体系统里的「总指挥」之一（另一类是 AutonomousPlanningAgent）：
  - 本类：人类写死的 plan() 步骤——清晰、可预期，适合生产流水线
  - Autonomous：让 LLM 自己决定何时调用哪些 tool——更灵活，也更难控

典型 Planning 模式（本文件）：
  1. Scanner 扫 RSS 并选出约 5 条 Deal
  2. 对每条用 Ensemble 估真价，算 discount = estimate - price
  3. 按折扣排序，若最佳折扣 > DEAL_THRESHOLD（50 美元）则 Messaging 告警

教学关键词：Orchestration（编排）、Pipeline（流水线）、Threshold（阈值过滤）。
"""

from typing import Optional, List
from agents.agent import Agent
from agents.deals import ScrapedDeal, DealSelection, Deal, Opportunity
from agents.scanner_agent import ScannerAgent
from agents.ensemble_agent import EnsembleAgent
from agents.messaging_agent import MessagingAgent


class PlanningAgent(Agent):
    """
    规划 Agent：协调扫描、集成估价与消息三个子 Agent。
    """

    name = "Planning Agent"
    color = Agent.GREEN
    # 折扣低于该美元数则不打扰用户（减少「假优惠」噪声）
    DEAL_THRESHOLD = 50

    def __init__(self, collection):
        """
        Create instances of the 3 Agents that this planner coordinates across

        参数:
            collection: Chroma products collection，传给 Ensemble（进而给 Frontier RAG）
        """
        self.log("Planning Agent is initializing")
        self.scanner = ScannerAgent()
        self.ensemble = EnsembleAgent(collection)
        self.messenger = MessagingAgent()
        self.log("Planning Agent is ready")

    def run(self, deal: Deal) -> Opportunity:
        """
        Run the workflow for a particular deal

        对单条 Deal：估真价 → 算折扣 → 打包成 Opportunity。

        参数:
            deal: 经 Scanner 结构化后的优惠
        返回:
            Opportunity（含 estimate 与 discount）
        """
        self.log("Planning Agent is pricing up a potential deal")
        estimate = self.ensemble.price(deal.product_description)
        discount = estimate - deal.price
        self.log(f"Planning Agent has processed a deal with discount ${discount:.2f}")
        return Opportunity(deal=deal, estimate=estimate, discount=discount)

    def plan(self, memory: List[str] = []) -> Optional[Opportunity]:
        """
        Run the full workflow:
        1. Use the ScannerAgent to find deals from RSS feeds
        2. Use the EnsembleAgent to estimate them
        3. Use the MessagingAgent to send a notification of deals

        参数:
            memory: 历史已推送机会（用于 Scanner 去重）
        返回:
            若最佳折扣超过阈值则返回该 Opportunity，否则 None
        """
        self.log("Planning Agent is kicking off a run")
        selection = self.scanner.scan(memory=memory)
        if selection:
            # 最多处理前 5 条，控制 API / GPU 成本
            opportunities = [self.run(deal) for deal in selection.deals[:5]]
            # 折扣从大到小：最「划算」的排第一
            opportunities.sort(key=lambda opp: opp.discount, reverse=True)
            best = opportunities[0]
            self.log(f"Planning Agent has identified the best deal has discount ${best.discount:.2f}")
            if best.discount > self.DEAL_THRESHOLD:
                self.messenger.alert(best)
            self.log("Planning Agent has completed a run")
            return best if best.discount > self.DEAL_THRESHOLD else None
        return None
