"""从 URL 抓取招聘启事内容。模式同第 1 周 scraper，但对职位文本提高了长度上限。"""
from bs4 import BeautifulSoup
import requests

# 招聘启事可能很长；允许超过默认的 2_000 字符
JOB_POST_CHAR_LIMIT = 8_000

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
}


def fetch_website_contents(url: str, char_limit: int = JOB_POST_CHAR_LIMIT) -> str:
    """
    返回给定 URL 页面的标题与主要文本。
    去除 script、style、图片等。截断到 char_limit。
    """
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    title = soup.title.string if soup.title else "No title found"
    if soup.body:
        for tag in soup.body(["script", "style", "img", "input", "nav", "footer"]):
            tag.decompose()
        text = soup.body.get_text(separator="\n", strip=True)
    else:
        text = ""
    return (title + "\n\n" + text)[:char_limit]
