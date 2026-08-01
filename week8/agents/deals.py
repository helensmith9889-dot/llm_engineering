"""
优惠交易（Deal）相关的数据结构与 RSS 抓取逻辑。

在「Price is Right」多智能体扫货系统中，本模块负责「数据层」：
  1. 从 DealNews 等 RSS 源拉取原始优惠条目（ScrapedDeal）
  2. 用 Pydantic 模型定义结构化的 Deal / DealSelection / Opportunity
     ——这些模型既给 Scanner Agent 做 Structured Outputs（结构化输出），
       也在 Planning / Messaging 之间传递「值得通知用户的机会」

教学关键词：
  - RSS feed：网站发布的内容订阅源，适合周期性抓新优惠
  - BeautifulSoup：解析 HTML，清洗摘要文本
  - Pydantic BaseModel：带类型与 Field 描述的数据类，可直接作为 LLM 的
    response_format，让模型按 schema 填字段
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Self
from bs4 import BeautifulSoup
import re
import feedparser
from tqdm import tqdm
import requests
import time

# DealNews 上电子产品 / 电脑 / 智能家居 三类 RSS；Scanner 会轮询这些源
feeds = [
    "https://www.dealnews.com/c142/Electronics/?rss=1",
    "https://www.dealnews.com/c39/Computers/?rss=1",
    "https://www.dealnews.com/f1912/Smart-Home/?rss=1",
]

# You could also add: "https://www.dealnews.com/c238/Automotive/?rss=1"
# "https://www.dealnews.com/c196/Home-Garden/?rss=1"


def extract(html_snippet: str) -> str:
    """
    用 BeautifulSoup 清洗 HTML 片段，提取可读的纯文本摘要。

    参数:
        html_snippet: RSS entry 里可能带标签的 summary HTML

    返回:
        去掉标签与换行后的一行纯文本；若找不到标准 snippet 结构则退回原文。

    为什么要清洗：把脏 HTML 直接丢给 LLM 会浪费 token，还容易干扰价格解析。
    """
    soup = BeautifulSoup(html_snippet, "html.parser")
    snippet_div = soup.find("div", class_="snippet summary")

    if snippet_div:
        description = snippet_div.get_text(strip=True)
        # 有时文本里还嵌着转义 HTML，再解析一次更干净
        description = BeautifulSoup(description, "html.parser").get_text()
        description = re.sub("<[^<]+?>", "", description)
        result = description.strip()
    else:
        result = html_snippet
    return result.replace("\n", " ")


class ScrapedDeal:
    """
    从 RSS 抓取到的「原始优惠」对象（尚未经 LLM 精选）。

    字段含义：
      title / summary：列表页信息
      url：优惠详情页链接（也用作 memory 去重键）
      details / features：详情页正文拆分出的描述与特性

    Scanner Agent 会批量 fetch，再交给 LLM 选出描述最清晰、价格最可信的几条。
    """

    category: str
    title: str
    summary: str
    url: str
    details: str
    features: str

    def __init__(self, entry: Dict[str, str]):
        """
        根据 feedparser 解析出的单条 entry 字典填充本实例。

        步骤：读标题与摘要 → 请求详情页 → 拆分 Details/Features → 截断长度。
        """
        self.title = entry["title"]
        self.summary = extract(entry["summary"])
        self.url = entry["links"][0]["href"]
        # 再请求详情页，拿到更完整的商品说明（给 LLM 写 product_description 用）
        stuff = requests.get(self.url).content
        soup = BeautifulSoup(stuff, "html.parser")
        content = soup.find("div", class_="content-section").get_text()
        content = content.replace("\nmore", "").replace("\n", " ")
        if "Features" in content:
            self.details, self.features = content.split("Features", 1)
        else:
            self.details = content
            self.features = ""
        self.truncate()

    def truncate(self):
        """
        把各字段截到合理长度，避免一次 prompt 塞入过多文本（省 token、降噪声）。
        """
        self.title = self.title[:100]
        self.details = self.details[:500]
        self.features = self.features[:500]

    def __repr__(self):
        """
        简短字符串表示，便于在调试打印时识别是哪条优惠。
        """
        return f"<{self.title}>"

    def describe(self):
        """
        生成给 LLM 阅读的较长描述（标题 + 详情 + 特性 + URL）。

        Scanner 的 user prompt 会把多条 describe() 结果拼在一起。
        """
        return f"Title: {self.title}\nDetails: {self.details.strip()}\nFeatures: {self.features.strip()}\nURL: {self.url}"

    @classmethod
    def fetch(cls, show_progress: bool = False) -> List[Self]:
        """
        从 feeds 列表中的所有 RSS 源抓取优惠。

        参数:
            show_progress: True 时用 tqdm 显示进度条

        返回:
            ScrapedDeal 列表；每个源最多取前 10 条，条目间 sleep 以免请求过猛。
        """
        deals = []
        feed_iter = tqdm(feeds) if show_progress else feeds
        for feed_url in feed_iter:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:10]:
                deals.append(cls(entry))
                time.sleep(0.05)
        return deals


class Deal(BaseModel):
    """
    经 LLM 精选并结构化后的「一条优惠」。

    Field(description=...) 里的英文说明会作为 Structured Outputs 的 schema
    提示词一部分，引导模型如何填写 product_description / price / url。
    注意：字面量保持英文（课程约定），勿改动这些 description 字符串。
    """

    product_description: str = Field(
        description="Your clearly expressed summary of the product in 3-4 sentences. Details of the item are much more important than why it's a good deal. Avoid mentioning discounts and coupons; focus on the item itself. There should be a short paragraph of text for each item you choose."
    )
    price: float = Field(
        description="The actual price of this product, as advertised in the deal. Be sure to give the actual price; for example, if a deal is described as $100 off the usual $300 price, you should respond with $200"
    )
    url: str = Field(description="The URL of the deal, as provided in the input")


class DealSelection(BaseModel):
    """
    LLM 选出的一批 Deal（通常目标是 5 条高质量、价格清晰的优惠）。

    ScannerAgent.scan() 把 response_format 设为本类型，模型必须返回符合 schema 的 JSON。
    """

    deals: List[Deal] = Field(
        description="Your selection of the 5 deals that have the most detailed, high quality description and the most clear price. You should be confident that the price reflects the deal, that it is a good deal, with a clear description"
    )


class Opportunity(BaseModel):
    """
    「捡漏机会」：一条 Deal，加上我们估算的真价与折扣空间。

    - deal: 原始优惠（描述、标价、链接）
    - estimate: Ensemble 等模型估出的「大概值多少钱」
    - discount: estimate - deal.price，越大越「划算」

    Planning Agent 用 discount 排序，超过阈值才让 Messaging Agent 通知用户。
    """

    deal: Deal
    estimate: float
    discount: float
