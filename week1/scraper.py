"""
第 1 周辅助模块：用 HTTP 请求抓取网页，再用 BeautifulSoup 清洗出纯文本。

本周核心技能（与 LLM 工程的关系）：
- HTTP 请求：从互联网拉取原始 HTML（LLM 本身不会“上网”，需要你先把网页变成文本）。
- BeautifulSoup 网页抓取：把杂乱的 HTML 解析成可读的标题与正文。
- 把网页文本喂给 LLM：清洗后的文本会进入 prompt，供模型做摘要、问答等任务。

注意：模型有「上下文窗口」（context window）限制——一次能读入的 token/字符有上限。
因此本模块会把正文截断到约 2000 字符，避免 prompt 过长导致报错或费用飙升。
"""

from bs4 import BeautifulSoup
import requests


# HTTP 请求头（headers）：模拟普通浏览器访问。
# 许多网站会检查 User-Agent；若不伪装，可能被拒绝或返回简化页面。
# 这些字段会随请求一起发给服务器，不影响页面逻辑，只影响“对方如何看待你”。
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
}


def fetch_website_contents(url):
    """
    抓取指定 URL 的网页标题与正文，并截断到 2000 字符。

    参数：
        url: 要抓取的网页地址（字符串），例如 "https://example.com"。

    返回：
        str: 「标题 + 空行 + 正文」拼成的字符串，总长度最多 2000 字符。

    为什么这样做：
        LLM 需要的是干净可读的文本，而不是带标签的 HTML。
        截断到 2000 字符是为了适配上下文窗口：网页往往很长，全量塞进 prompt
        既浪费 token，也可能超出模型一次能处理的长度。
    """
    # 1) 发送 GET 请求，拿到服务器返回的原始 HTML（bytes）
    response = requests.get(url, headers=headers)
    # 2) 用 BeautifulSoup 把 HTML 解析成可查询的文档树
    soup = BeautifulSoup(response.content, "html.parser")
    # 3) 取 <title>；有的页面没有标题，给一个兜底文案
    title = soup.title.string if soup.title else "No title found"
    if soup.body:
        # 4) 删除对 LLM 无用的节点：脚本、样式、图片、输入框等
        # decompose() 会从文档树中彻底移除该标签及其子内容（不是隐藏，是删掉）
        for irrelevant in soup.body(["script", "style", "img", "input"]):
            irrelevant.decompose()
        # 5) 从 <body> 提取纯文本；换行分隔，并去掉首尾空白
        text = soup.body.get_text(separator="\n", strip=True)
    else:
        # 极少数页面没有 <body>，正文就置为空
        text = ""
    # 6) 标题与正文拼接后截断：[:2_000] 即只保留前 2000 个字符
    # 下划线写法 2_000 与 2000 等价，只是更易读
    return (title + "\n\n" + text)[:2_000]


def fetch_website_links(url):
    """
    抓取指定 URL 页面上所有超链接（<a href="...">）的地址列表。

    参数：
        url: 要抓取的网页地址（字符串）。

    返回：
        list[str]: 非空的链接字符串列表（可能是相对路径或绝对 URL）。

    说明：
        这里会再次请求并解析同一页面，确实有些“重复劳动”。
        课程刻意保持简单，方便实验；你完全可以改成类、缓存 soup 来优化。
        收集链接常见用途：让 LLM 决定下一步该打开哪些子页面（brochure / agent 流程）。
    """
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")
    # find_all("a") 找出所有锚点；link.get("href") 读取链接地址（可能为 None）
    links = [link.get("href") for link in soup.find_all("a")]
    # 过滤掉空值 / 假值，只保留真实存在的 href
    return [link for link in links if link]
