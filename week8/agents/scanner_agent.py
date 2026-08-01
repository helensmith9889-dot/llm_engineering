"""
Scanner Agent（扫描 Agent）：从 RSS 抓取优惠，并用 LLM 精选出高质量 Deal。

在「Price is Right」多智能体流水线中的位置：
  RSS 抓取 → 本 Agent（Structured Outputs 选出约 5 条）→ Planning 估价 → Messaging 通知

Scanner 解决的痛点：
  RSS 一次可能吐出几十条嘈杂优惠（折扣文案、$XX off、描述残缺……）。
  若全部丢给估价模型，又贵又慢；所以先用较便宜的模型做「质检+摘要」，只留约 5 条。

教学要点：
  - 多智能体分工：Scanner 只负责「发现与筛选」，不负责估价或通知
  - Structured Outputs：response_format=DealSelection，强制模型返回合法 JSON schema
    （比「请返回 JSON」口头约束可靠——SDK 按 Pydantic 模型解析）
  - memory：已推送过的 URL 列表，避免重复骚扰用户
  - 价格陷阱：文案写「$200 off」不是成交价；提示词反复强调只选「高度确信的真实标价」
"""

from typing import Optional, List
from openai import OpenAI
from agents.deals import ScrapedDeal, DealSelection
from agents.agent import Agent


class ScannerAgent(Agent):
    """
    扫描 Agent：抓 RSS + 调用 OpenAI 选出描述清晰、价格可信的优惠。
    """

    MODEL = "gpt-5-mini"

    # 系统提示：强调选「描述详细 + 价格清晰」的 5 条；字面量保持英文勿改
    SYSTEM_PROMPT = """You identify and summarize the 5 most detailed deals from a list, by selecting deals that have the most detailed, high quality description and the most clear price.
    Respond strictly in JSON with no explanation, using this format. You should provide the price as a number derived from the description. If the price of a deal isn't clear, do not include that deal in your response.
    Most important is that you respond with the 5 deals that have the most detailed product description with price. It's not important to mention the terms of the deal; most important is a thorough description of the product.
    Be careful with products that are described as "$XXX off" or "reduced by $XXX" - this isn't the actual price of the product. Only respond with products when you are highly confident about the price. 
    """

    USER_PROMPT_PREFIX = """Respond with the most promising 5 deals from this list, selecting those which have the most detailed, high quality product description and a clear price that is greater than 0.
    You should rephrase the description to be a summary of the product itself, not the terms of the deal.
    Remember to respond with a short paragraph of text in the product_description field for each of the 5 items that you select.
    Be careful with products that are described as "$XXX off" or "reduced by $XXX" - this isn't the actual price of the product. Only respond with products when you are highly confident about the price. 
    
    Deals:
    
    """

    USER_PROMPT_SUFFIX = "\n\nInclude exactly 5 deals, no more."

    name = "Scanner Agent"
    color = Agent.CYAN

    def __init__(self):
        """
        Set up this instance by initializing OpenAI

        只创建客户端；真正的网络抓取与模型调用发生在 scan() / fetch_deals()。
        """
        self.log("Scanner Agent is initializing")
        self.openai = OpenAI()
        self.log("Scanner Agent is ready")

    def fetch_deals(self, memory) -> List[ScrapedDeal]:
        """
        Look up deals published on RSS feeds
        Return any new deals that are not already in the memory provided

        两步：ScrapedDeal.fetch() 拉 RSS → 用 memory 里已有 URL 做差集过滤。

        参数:
            memory: 历史 Opportunity 列表（含已推送 URL）；用于去重
        返回:
            尚未出现在 memory 里的 ScrapedDeal 列表
        """
        self.log("Scanner Agent is about to fetch deals from RSS feed")
        urls = [opp.deal.url for opp in memory]
        scraped = ScrapedDeal.fetch()
        # 列表推导：只保留新 URL，实现「不重复扫同一条优惠」
        result = [scrape for scrape in scraped if scrape.url not in urls]
        self.log(f"Scanner Agent received {len(result)} deals not already scraped")
        return result

    def make_user_prompt(self, scraped) -> str:
        """
        Create a user prompt for OpenAI based on the scraped deals provided

        把每条 ScrapedDeal.describe() 拼进前缀与后缀之间，形成完整 user 消息。
        前缀说明「怎么选」，中间是候选列表，后缀再次强调「只要 5 条」。
        """
        user_prompt = self.USER_PROMPT_PREFIX
        user_prompt += "\n\n".join([scrape.describe() for scrape in scraped])
        user_prompt += self.USER_PROMPT_SUFFIX
        return user_prompt

    def scan(self, memory: List[str] = []) -> Optional[DealSelection]:
        """
        Call OpenAI to provide a high potential list of deals with good descriptions and prices
        Use StructuredOutputs to ensure it conforms to our specifications

        流程：
          1. fetch_deals 去重抓取
          2. 若有新货，拼 prompt，用 chat.completions.parse + DealSelection 做结构化输出
          3. 再过滤 price>0，防止模型偶发返回 0/负价

        参数:
            memory: 已处理过的优惠记忆（实际传入的是 Opportunity 列表，见 fetch_deals）
        返回:
            DealSelection；若没有新货则 None。价格 ≤0 的条目会被过滤掉。
        """
        scraped = self.fetch_deals(memory)
        if scraped:
            user_prompt = self.make_user_prompt(scraped)
            self.log("Scanner Agent is calling OpenAI using Structured Outputs")
            # parse + response_format：SDK 按 Pydantic 模型解析结构化结果
            # reasoning_effort="minimal"：本任务偏抽取/筛选，不需要长推理链
            result = self.openai.chat.completions.parse(
                model=self.MODEL,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=DealSelection,
                reasoning_effort="minimal",
            )
            result = result.choices[0].message.parsed
            result.deals = [deal for deal in result.deals if deal.price > 0]
            self.log(
                f"Scanner Agent received {len(result.deals)} selected deals with price>0 from OpenAI"
            )
            return result
        return None

    def test_scan(self, memory: List[str] = []) -> Optional[DealSelection]:
        """
        Return a test DealSelection, to be used during testing

        离线测试用：不访问网络与 API，直接返回硬编码的示例优惠列表。
        便于在没有 RSS/密钥时调试 Planning / UI 后续环节。
        """
        results = {
            "deals": [
                {
                    "product_description": "The Hisense R6 Series 55R6030N is a 55-inch 4K UHD Roku Smart TV that offers stunning picture quality with 3840x2160 resolution. It features Dolby Vision HDR and HDR10 compatibility, ensuring a vibrant and dynamic viewing experience. The TV runs on Roku's operating system, allowing easy access to streaming services and voice control compatibility with Google Assistant and Alexa. With three HDMI ports available, connecting multiple devices is simple and efficient.",
                    "price": 178,
                    "url": "https://www.dealnews.com/products/Hisense/Hisense-R6-Series-55-R6030-N-55-4-K-UHD-Roku-Smart-TV/484824.html?iref=rss-c142",
                },
                {
                    "product_description": "The Poly Studio P21 is a 21.5-inch LED personal meeting display designed specifically for remote work and video conferencing. With a native resolution of 1080p, it provides crystal-clear video quality, featuring a privacy shutter and stereo speakers. This display includes a 1080p webcam with manual pan, tilt, and zoom control, along with an ambient light sensor to adjust the vanity lighting as needed. It also supports 5W wireless charging for mobile devices, making it an all-in-one solution for home offices.",
                    "price": 30,
                    "url": "https://www.dealnews.com/products/Poly-Studio-P21-21-5-1080-p-LED-Personal-Meeting-Display/378335.html?iref=rss-c39",
                },
                {
                    "product_description": "The Lenovo IdeaPad Slim 5 laptop is powered by a 7th generation AMD Ryzen 5 8645HS 6-core CPU, offering efficient performance for multitasking and demanding applications. It features a 16-inch touch display with a resolution of 1920x1080, ensuring bright and vivid visuals. Accompanied by 16GB of RAM and a 512GB SSD, the laptop provides ample speed and storage for all your files. This model is designed to handle everyday tasks with ease while delivering an enjoyable user experience.",
                    "price": 446,
                    "url": "https://www.dealnews.com/products/Lenovo/Lenovo-Idea-Pad-Slim-5-7-th-Gen-Ryzen-5-16-Touch-Laptop/485068.html?iref=rss-c39",
                },
                {
                    "product_description": "The Dell G15 gaming laptop is equipped with a 6th-generation AMD Ryzen 5 7640HS 6-Core CPU, providing powerful performance for gaming and content creation. It features a 15.6-inch 1080p display with a 120Hz refresh rate, allowing for smooth and responsive gameplay. With 16GB of RAM and a substantial 1TB NVMe M.2 SSD, this laptop ensures speedy performance and plenty of storage for games and applications. Additionally, it includes the Nvidia GeForce RTX 3050 GPU for enhanced graphics and gaming experiences.",
                    "price": 650,
                    "url": "https://www.dealnews.com/products/Dell/Dell-G15-Ryzen-5-15-6-Gaming-Laptop-w-Nvidia-RTX-3050/485067.html?iref=rss-c39",
                },
            ]
        }
        return DealSelection(**results)
