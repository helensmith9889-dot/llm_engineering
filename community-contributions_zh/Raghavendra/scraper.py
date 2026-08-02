from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin, urlparse

# 抓取网页时使用的标准请求头
headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/117.0.0.0 Safari/537.36"
    )
}


def fetch_website_contents(url, max_chars=2000):
    """
    返回网页标题 + 清洗后的正文。
    自动移除 script、style、img、nav、footer 等。
    截断到 max_chars。
    """
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        return f"Failed to fetch {url}: {e}"

    soup = BeautifulSoup(response.content, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else "No title found"

    # 移除无关元素
    remove_tags = ["script", "style", "img", "input", "nav", "footer", "form"]
    for tag in soup(remove_tags):
        tag.decompose()

    # 提取文本并去掉空行
    text = soup.get_text(separator="\n", strip=True)
    text = "\n".join(line for line in text.splitlines() if line.strip())  # 去掉空白行

    return (title + "\n\n" + text)[:max_chars]


def fetch_website_links(url):
    """
    返回页面上清洗后的有效绝对链接列表。
    过滤：
    - 邮箱（mailto:）
    - 电话（tel:）
    - pdf、文件、图片
    - 登录、隐私、条款、cookie 页面
    - 社交媒体链接（可选）
    """
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch links from {url}: {e}")
        return []

    soup = BeautifulSoup(response.content, "html.parser")
    raw_links = [a.get("href") for a in soup.find_all("a") if a.get("href")]

    cleaned_links = []
    for link in raw_links:
        # 相对路径 → 绝对 URL
        full_url = urljoin(url, link)

        # 去掉追踪参数与 fragment
        parsed = urlparse(full_url)
        full_url = parsed.scheme + "://" + parsed.netloc + parsed.path

        # 跳过不想要的链接
        skip_keywords = [
            "mailto:", "tel:", ".pdf", ".jpg", ".png", ".jpeg",
            "privacy", "terms", "login", "signup", "cookie"
        ]
        if any(skip in full_url.lower() for skip in skip_keywords):
            continue

        if full_url not in cleaned_links:
            cleaned_links.append(full_url)

    return cleaned_links
