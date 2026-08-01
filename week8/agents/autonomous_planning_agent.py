"""
Autonomous Planning Agent（自主规划 Agent）：由 LLM 通过 Tool Calling 自主编排扫货流程。

与 PlanningAgent（固定流水线）对比：
  - PlanningAgent：代码写死「先扫 → 再估 → 再通知」——顺序由程序员决定
  - 本类：把 scan / estimate / notify 注册成 tools，由 gpt 决定调用顺序与参数
    ——顺序由模型在对话中「边想边调工具」决定

这是典型的 Agentic Workflow（智能体工作流）/ Tool Use 循环：
  1. 把任务与可用工具描述发给 LLM
  2. 若 finish_reason == "tool_calls"：模型请求调用某个函数
  3. 本地真正执行该函数，把结果以 role="tool" 消息塞回 messages
  4. 再调用 LLM……直到它不再要工具，而是给出最终文本（如 "OK"）

教学关键词：Function Calling / Tool Use、ReAct 式循环、多智能体协作中的「大脑」角色。
注意：自主不等于可靠——模型可能重复 notify 或跳过估价，所以 notify 里有「只通知一次」防护。
"""

from typing import Optional, List, Dict
from agents.agent import Agent
from agents.deals import Deal, Opportunity
from agents.scanner_agent import ScannerAgent
from agents.ensemble_agent import EnsembleAgent
from agents.messaging_agent import MessagingAgent
from openai import OpenAI
import json


class AutonomousPlanningAgent(Agent):
    """
    自主规划 Agent：持有三个子 Agent，并向 OpenAI 暴露对应 tools。

    子 Agent 分工（本类只编排，不自己抓 RSS / 估向量价）：
      Scanner  → 发现优惠
      Ensemble → 估计「真价」
      Messenger→ 推送通知
    """

    name = "Autonomous Planning Agent"
    color = Agent.GREEN
    MODEL = "gpt-5.1"

    def __init__(self, collection):
        """
        Create instances of the 3 Agents that this planner coordinates across

        同时创建 OpenAI 客户端；memory / opportunity 在每次 plan() 开始时重置。
        collection 传给 EnsembleAgent，供 Frontier 分支做 RAG 相似商品检索。
        """
        self.log("Autonomous Planning Agent is initializing")
        self.scanner = ScannerAgent()
        self.ensemble = EnsembleAgent(collection)
        self.messenger = MessagingAgent()
        self.openai = OpenAI()
        # memory：扫描去重用；opportunity：本次 run 是否已选出并通知过的那条机会
        self.memory = None
        self.opportunity = None
        self.log("Autonomous Planning Agent is ready")

    def scan_the_internet_for_bargains(self) -> str:
        """
        Run the tool to scan

        Tool：调用 Scanner，把 DealSelection 序列化为 JSON 字符串返回给 LLM。
        必须返回字符串/可序列化内容——工具结果会作为下一条消息的 content 喂回模型。
        """
        self.log("Autonomous Planning agent is calling scanner")
        results = self.scanner.scan(memory=self.memory)
        return results.model_dump_json() if results else "No deals found"

    def estimate_true_value(self, description: str) -> str:
        """
        Run the tool to estimate true value

        Tool：用 Ensemble 估真价，返回人类可读字符串供模型继续推理
        （模型下一步常会比较 deal_price 与 estimate，选出折扣最大的一条）。
        """
        self.log("Autonomous Planning agent is estimating value via Ensemble Agent")
        estimate = self.ensemble.price(description)
        return f"The estimated true value of {description} is {estimate}"

    def notify_user_of_deal(
        self, description: str, deal_price: float, estimated_true_value: float, url: str
    ) -> Dict:
        """
        Run the tool to notify the user

        Tool：只应调用一次；若已有 opportunity 则忽略第二次，防止刷屏。
        成功时写入 self.opportunity，供 plan() 最终返回给框架/UI。

        discount（折扣空间）= 估计真价 − 标价；正且越大，越像「捡漏」。
        """
        if self.opportunity:
            self.log("Autonomous Planning agent is trying to notify the user a 2nd time; ignoring")
        else:
            self.log("Autonomous Planning agent is notifying user")
            self.messenger.notify(description, deal_price, estimated_true_value, url)
            deal = Deal(product_description=description, price=deal_price, url=url)
            discount = estimated_true_value - deal_price
            self.opportunity = Opportunity(
                deal=deal, estimate=estimated_true_value, discount=discount
            )
        return "Notification sent ok"

    # ---- 以下三个 dict 是 OpenAI tools 的 JSON Schema（字面量保持英文）----
    # 模型靠 name/description/parameters 理解「能调什么、要传哪些参数」；
    # 这不是 Python 函数本身，而是发给 API 的工具说明书。

    scan_function = {
        "name": "scan_the_internet_for_bargains",
        "description": "Returns top bargains scraped from the internet along with the price each item is being offered for",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    }

    estimate_function = {
        "name": "estimate_true_value",
        "description": "Given the description of an item, estimate how much it is actually worth",
        "parameters": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "The description of the item to be estimated",
                },
            },
            "required": ["description"],
            "additionalProperties": False,
        },
    }

    notify_function = {
        "name": "notify_user_of_deal",
        "description": "Send the user a push notification about the single most compelling deal; only call this one time",
        "parameters": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "The description of the item itself scraped from the internet",
                },
                "deal_price": {
                    "type": "number",
                    "description": "The price offered by this deal scraped from the internet",
                },
                "estimated_true_value": {
                    "type": "number",
                    "description": "The estimated actual value that this is worth",
                },
                "url": {
                    "type": "string",
                    "description": "The URL of this deal as scraped from the internet",
                },
            },
            "required": ["description", "deal_price", "estimated_true_value", "url"],
            "additionalProperties": False,
        },
    }

    def get_tools(self):
        """
        Return the json for the tools to be used

        组装 chat.completions 所需的 tools 列表（每项 type=function + function schema）。
        """
        return [
            {"type": "function", "function": self.scan_function},
            {"type": "function", "function": self.estimate_function},
            {"type": "function", "function": self.notify_function},
        ]

    def handle_tool_call(self, message):
        """
        Actually call the tools associated with this message

        解析模型返回的 tool_calls：按名字映射到本地方法，执行后拼成 role=tool 的消息。
        每条结果必须带上 tool_call_id，API 才能把「这次调用」和「这次返回」对齐。
        """
        mapping = {
            "scan_the_internet_for_bargains": self.scan_the_internet_for_bargains,
            "estimate_true_value": self.estimate_true_value,
            "notify_user_of_deal": self.notify_user_of_deal,
        }
        results = []
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            # arguments 是 JSON 字符串，例如 {"description": "..."}
            arguments = json.loads(tool_call.function.arguments)
            tool = mapping.get(tool_name)
            # 有参数则 **arguments 解包；未知工具则返回空串
            result = tool(**arguments) if tool else ""
            results.append({"role": "tool", "content": result, "tool_call_id": tool_call.id})
        return results

    # 系统 / 用户指令：字面量保持英文（发给模型的 prompt）
    # 这里用自然语言规定「理想流程」，但模型仍可能调整顺序——这就是自主规划的弹性与风险
    system_message = "You find great deals on bargain products using your tools, and notify the user of the best bargain."
    user_message = """
    First, use your tool to scan the internet for bargain deals. Then for each deal, use your tool to estimate its true value.
    Then pick the single most compelling deal where the price is much lower than the estimated true value, and use your tool to notify the user.
    Then just reply OK to indicate success.
    """
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message},
    ]

    def plan(self, memory: List[str] = []) -> Optional[Opportunity]:
        """
        Run the full workflow, providing the LLM with tools to surface scraped deals to the user

        自主循环：不断 chat + 处理 tool_calls，直到模型给出最终文本回复。

        参数:
            memory: 历史 URL / 机会记忆，供扫描去重（实际常为 Opportunity 列表，见 Scanner）
        返回:
            若成功 notify 过则返回 Opportunity，否则 None
        """
        self.log("Autonomous Planning Agent is kicking off a run")
        self.memory = memory
        self.opportunity = None
        # 复制类级初始 messages，避免多次 plan() 互相污染对话历史
        messages = self.messages[:]
        done = False
        while not done:
            response = self.openai.chat.completions.create(
                model=self.MODEL, messages=messages, tools=self.get_tools()
            )
            # finish_reason 为 tool_calls 表示「先别结束，请帮我执行这些函数」
            if response.choices[0].finish_reason == "tool_calls":
                message = response.choices[0].message
                results = self.handle_tool_call(message)
                # 必须把「助手的 tool 请求」和「工具结果」都追加进对话历史
                messages.append(message)
                messages.extend(results)
            else:
                # 模型输出普通文本（如 OK）→ 任务宣告完成，退出循环
                done = True
        reply = response.choices[0].message.content
        self.log(f"Autonomous Planning Agent completed with: {reply}")
        return self.opportunity
