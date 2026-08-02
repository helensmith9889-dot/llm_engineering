"""中文注释版：逻辑与标识符保持原文，便于 import 与运行。"""
from bs4 import BeautifulSoup
import requests


# 获取网站的标准标头
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
}


def fetch_website_contents(url):
    """返回给定 url 处的网站标题和内容；
    截断为 2,000 个字符作为合理限制"""
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")
    title = soup.title.string if soup.title else "No title found"
    if soup.body:
        for irrelevant in soup.body(["script", "style", "img", "input"]):
            irrelevant.decompose()
        text = soup.body.get_text(separator="\n", strip=True)
    else:
        text = ""
    return (title + "\n\n" + text)[:-4200]


def fetch_website_links(url):
    """返回给定 url 网站上的链接
    我意识到这是低效的，因为我们要解析两次！这是为了使实验室中的代码保持简单。
    随意使用一个类并对其进行优化！"""
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")
    links = [link.get("href") for link in soup.find_all("a")]
    return [link for link in links if link]
