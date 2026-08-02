"""中文注释版：逻辑与标识符保持原文，便于 import 与运行。"""
import time

from bs4 import BeautifulSoup
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


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
    return (title + "\n\n" + text)[:2_000]


def fetch_website_links(url):
    """返回给定 url 网站上的链接
    我意识到这是低效的，因为我们要解析两次！这是为了使实验室中的代码保持简单。
    随意使用一个类并对其进行优化！"""
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")
    links = [link.get("href") for link in soup.find_all("a")]
    return [link for link in links if link]


def fetch_website_contents_selenium(url):
    """使用 Selenium 返回给定 url 处的网站标题和内容。
    处理 JavaScript 密集型网站。截断为 2,000 个字符。"""
    # 配置无头 Chrome（匹配 day1_selenium_implementation）
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    # 启动 Selenium WebDriver
    driver.get(url)
    
    # 等待JS加载（根据需要调整）
    time.sleep(3)
    
    # JS执行后获取页面源码
    page_source = driver.page_source
    driver.quit()
    
    # 使用 BeautifulSoup 解析 HTML 内容
    soup = BeautifulSoup(page_source, 'html.parser')
    title = soup.title.string if soup.title else "No title found"
    if soup.body:
        for irrelevant in soup.body(["script", "style", "img", "input"]):
            irrelevant.decompose()
        text = soup.body.get_text(separator="\n", strip=True)
    else:
        text = ""
    return (title + "\n\n" + text)[:2_000]
