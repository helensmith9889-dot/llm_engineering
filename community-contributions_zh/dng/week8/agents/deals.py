import re
import time
from typing import Dict, List, Self

import feedparser
import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from tqdm import tqdm

feeds = [
    "https://www.dealnews.com/c142/Electronics/?rss=1",
    "https://www.dealnews.com/c39/Computers/?rss=1",
    "https://www.dealnews.com/f1912/Smart-Home/?rss=1",
]

# 您还可以添加：“https://www.dealnews.com/c238/Automotive/?rss=1”
# “https://www.dealnews.com/c196/Home-Garden/?rss=1”


def extract(html_snippet: str) -> str:
    """使用 Beautiful Soup 清理此 HTML 片段并提取有用的文本"""
    soup = BeautifulSoup(html_snippet, "html.parser")
    snippet_div = soup.find("div", class_="snippet summary")

    if snippet_div:
        description = snippet_div.get_text(strip=True)
        description = BeautifulSoup(description, "html.parser").get_text()
        description = re.sub("<[^<]+?>", "", description)
        result = description.strip()
    else:
        result = html_snippet
    return result.replace("\n", " ")


class ScrapedDeal:
    """表示从 RSS feed 检索到的 Deal 的类"""

    category: str
    title: str
    summary: str
    url: str
    details: str
    features: str

    def __init__(self, entry: Dict[str, str]):
        """根据提供的字典填充此实例"""
        self.title = entry["title"]
        self.summary = extract(entry["summary"])
        self.url = entry["links"][0]["href"]
        try:
            stuff = requests.get(self.url, timeout=10).content
            soup = BeautifulSoup(stuff, "html.parser")
            content_div = soup.find("div", class_="content-section")
            if content_div:
                content = content_div.get_text()
            else:
                content_div = soup.find("div", class_="summary") or soup.find("article")
                content = content_div.get_text() if content_div else self.summary
        except Exception:
            content = self.summary
        content = content.replace("\nmore", "").replace("\n", " ")
        if "Features" in content:
            self.details, self.features = content.split("Features", 1)
        else:
            self.details = content
            self.features = ""
        self.truncate()

    def truncate(self):
        """将字段限制在合理的长度，以避免向模型发送太多信息"""
        self.title = self.title[:100]
        self.details = self.details[:500]
        self.features = self.features[:500]

    def __repr__(self):
        """返回一个字符串来描述这笔交易"""
        return f"<{self.title}>"

    def describe(self):
        """返回一个较长的字符串来描述此交易以用于调用模型"""
        return f"Title: {self.title}\nDetails: {self.details.strip()}\nFeatures: {self.features.strip()}\nURL: {self.url}"

    @classmethod
    def fetch(cls, show_progress: bool = False) -> List[Self]:
        """从选定的 RSS 源检索所有交易"""
        deals = []
        feed_iter = tqdm(feeds) if show_progress else feeds
        for feed_url in feed_iter:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:10]:
                deals.append(cls(entry))
                time.sleep(0.05)
        return deals


class Deal(BaseModel):
    """代表交易并带有摘要描述的类"""

    product_description: str = Field(
        description="Your clearly expressed summary of the product in 3-4 sentences. Details of the item are much more important than why it's a good deal. Avoid mentioning discounts and coupons; focus on the item itself. There should be a short paragraph of text for each item you choose."
    )
    price: float = Field(
        description="The actual price of this product, as advertised in the deal. Be sure to give the actual price; for example, if a deal is described as $100 off the usual $300 price, you should respond with $200"
    )
    url: str = Field(description="The URL of the deal, as provided in the input")


class DealSelection(BaseModel):
    """代表交易列表的类"""

    deals: List[Deal] = Field(
        description="Your selection of the 5 deals that have the most detailed, high quality description and the most clear price. You should be confident that the price reflects the deal, that it is a good deal, with a clear description"
    )


class Opportunity(BaseModel):
    """代表可能机会的类：我们估计的交易
    它的价格应该比所提供的要高"""

    deal: Deal
    estimate: float
    discount: float
