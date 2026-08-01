"""
第 2 周辅助模块：用 HTTP 请求抓取网页，再用 BeautifulSoup 清洗出纯文本与链接。

本周核心技能（与 LLM 工程的关系）：
- HTTP 请求：把远程网页拉到本地，作为 LLM 的外部知识来源。
- BeautifulSoup 网页抓取：从 HTML 中提取标题、正文，并收集超链接。
- 把网页文本喂给 LLM：清洗后的内容进入 prompt；链接列表可交给模型挑选
  下一步要打开的页面（例如生成公司宣传册 brochure 的多页抓取流程）。

注意上下文窗口：正文默认截断到 2000 字符，避免一次塞入过长网页。
"""

from bs4 import BeautifulSoup
import requests


# HTTP 请求头：用浏览器身份访问，降低被网站拦截或返回异常页面的概率
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
}


def fetch_website_contents(url):
    """
    抓取指定 URL 的网页标题与正文，并截断到 2000 字符。

    参数：
        url: 要抓取的网页地址（字符串）。

    返回：
        str: 「标题 + 空行 + 正文」，最多 2000 字符。

    为什么截断：
        LLM 的上下文窗口有限；网页全文往往很长。
        先截到合理长度，再拼进 prompt，是工程上常见的保护措施。
    """
    # GET 请求：headers 告诉服务器“我像浏览器”，response.content 是原始 HTML 字节
    response = requests.get(url, headers=headers)
    # 解析 HTML，得到可按标签查询的 soup 对象
    soup = BeautifulSoup(response.content, "html.parser")
    title = soup.title.string if soup.title else "No title found"
    if soup.body:
        # decompose()：从 DOM 树删除无关标签，避免脚本/样式污染给 LLM 的文本
        for irrelevant in soup.body(["script", "style", "img", "input"]):
            irrelevant.decompose()
        # 提取纯文本；separator 控制块之间如何换行
        text = soup.body.get_text(separator="\n", strip=True)
    else:
        text = ""
    # [:2_000]：只保留前 2000 字符，适配上下文窗口
    return (title + "\n\n" + text)[:2_000]


def fetch_website_links(url):
    """
    返回指定网页上所有非空超链接（href）。

    参数：
        url: 要抓取的网页地址。

    返回：
        list[str]: 链接字符串列表（可能含相对路径）。

    说明：
        为保持实验代码简单，这里会再次请求并解析同一页面（有些低效）。
        欢迎你用类封装、缓存解析结果来优化。
        在第 2 周 brochure 流程里，链接会交给 LLM 判断哪些子页值得继续抓取。
    """
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")
    # 遍历所有 <a>，取出 href 属性
    links = [link.get("href") for link in soup.find_all("a")]
    # 去掉 None / 空字符串，只留下有效链接
    return [link for link in links if link]
