"""
Messaging Agent（消息 Agent）：把「捡漏机会」推送给真人用户。

在多智能体扫货流水线末尾：
  Scanner 发现 → Ensemble 估价 → Planning 选出最佳 → 本 Agent 发 Push

实现方式：
  1. 可选：用 Claude（经 LiteLLM）把优惠写成 2–3 句激动人心的短文案
  2. 通过 Pushover HTTP API 发手机推送（音效 cashregister，很有「成交」感）

教学要点：Agent 不只调用 LLM，也可以调用外部工具（Tool Use）——这里工具是通知 API。
环境变量：PUSHOVER_USER / PUSHOVER_TOKEN。
"""

import os
from agents.deals import Opportunity
from agents.agent import Agent
from litellm import completion
import requests

# Pushover 官方发信端点
pushover_url = "https://api.pushover.net/1/messages.json"


class MessagingAgent(Agent):
    """
    消息通知 Agent：Pushover 推送 +（可选）LLM 润色文案。
    """

    name = "Messaging Agent"
    color = Agent.WHITE
    MODEL = "claude-sonnet-4-5"

    def __init__(self):
        """
        Set up this object to either do push notifications via Pushover,
        or SMS via Twilio,
        whichever is specified in the constants

        （中文补充）当前实现以 Pushover 为主；从环境变量读取 user/token。
        """
        self.log("Messaging Agent is initializing")
        self.pushover_user = os.getenv("PUSHOVER_USER", "your-pushover-user-if-not-using-env")
        self.pushover_token = os.getenv("PUSHOVER_TOKEN", "your-pushover-user-if-not-using-env")
        self.log("Messaging Agent has initialized Pushover and Claude")

    def push(self, text):
        """
        Send a Push Notification using the Pushover API

        参数:
            text: 推送正文
        """
        self.log("Messaging Agent is sending a push notification")
        payload = {
            "user": self.pushover_user,
            "token": self.pushover_token,
            "message": text,
            "sound": "cashregister",
        }
        requests.post(pushover_url, data=payload)

    def alert(self, opportunity: Opportunity):
        """
        Make an alert about the specified Opportunity

        用固定模板拼接价格 / 估价 / 折扣 / 简述 / URL，适合 PlanningAgent 直接调用。
        """
        text = f"Deal Alert! Price=${opportunity.deal.price:.2f}, "
        text += f"Estimate=${opportunity.estimate:.2f}, "
        text += f"Discount=${opportunity.discount:.2f} :"
        text += opportunity.deal.product_description[:10] + "... "
        text += opportunity.deal.url
        self.push(text)
        self.log("Messaging Agent has completed")

    def craft_message(
        self, description: str, deal_price: float, estimated_true_value: float
    ) -> str:
        """
        请 Claude 把优惠写成 2–3 句推送文案（只返回正文，不要多余解释）。

        供 AutonomousPlanningAgent 的 notify 路径使用，文案更「激动人心」。
        """
        user_prompt = "Please summarize this great deal in 2-3 sentences to be sent as an exciting push notification alerting the user about this deal.\n"
        user_prompt += f"Item Description: {description}\nOffered Price: {deal_price}\nEstimated true value: {estimated_true_value}"
        user_prompt += "\n\nRespond only with the 2-3 sentence message which will be used to alert & excite the user about this deal"
        response = completion(
            model=self.MODEL,
            messages=[
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content

    def notify(self, description: str, deal_price: float, estimated_true_value: float, url: str):
        """
        Make an alert about the specified details

        先 LLM 润色，再截断正文并附上 URL 推送。
        参数与 AutonomousPlanningAgent 的 tool schema 对齐。
        """
        self.log("Messaging Agent is using Claude to craft the message")
        text = self.craft_message(description, deal_price, estimated_true_value)
        self.push(text[:200] + "... " + url)
        self.log("Messaging Agent has completed")
