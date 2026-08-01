"""
第 1 周参考解答：用本地 Ollama（兼容 OpenAI SDK）对网页做幽默摘要。

本周核心技能（与 LLM 工程的关系）：
- 先用 scraper 通过 HTTP + BeautifulSoup 拿到干净网页文本；
- 再把文本放进 prompt（system / user 消息），交给 LLM 生成摘要；
- 体会「抓取 → 清洗 → 喂给模型」这条最基础的 LLM 应用流水线。

运行前提：本机已启动 Ollama，并拉取了 MODEL 指定的模型（默认 llama3.2）。
"""

from openai import OpenAI
from scraper import fetch_website_contents

# Ollama 提供与 OpenAI 兼容的本地 HTTP API；base_url 指向本机 11434 端口的 /v1
OLLAMA_BASE_URL = "http://localhost:11434/v1"
# 要调用的本地模型名称（需已在 Ollama 中 pull）
MODEL = "llama3.2"

# system prompt：设定助手角色与输出风格（影响模型“怎么说”）
system_prompt = """
You are a snarky assistant that analyzes the contents of a website,
and provides a short, snarky, humorous summary, ignoring text that might be navigation related.
Respond in markdown. Do not wrap the markdown in a code block - respond just with the markdown.
"""

# user prompt 前缀：说明任务；后面会拼上抓取到的网页正文
user_prompt_prefix = """
Here are the contents of a website.
Provide a short summary of this website.
If it includes news or announcements, then summarize these too.

"""


def messages_for(website):
    """
    组装发给聊天模型的 messages 列表（OpenAI Chat Completions 格式）。

    参数：
        website: 已抓取并清洗好的网页文本（通常来自 fetch_website_contents）。

    返回：
        list[dict]: 包含 system 与 user 两条消息的列表。

    为什么要分 system / user：
        system 负责定角色与规则；user 负责提供具体网页内容与任务。
        这是调用 LLM 时最常见的结构化输入方式。
    """
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt_prefix + website}
    ]


def summarize(url):
    """
    抓取网页并用本地 Ollama 模型生成摘要。

    参数：
        url: 目标网页地址。

    返回：
        str: 模型生成的摘要文本（markdown）。

    流程说明：
        1. 创建指向 Ollama 的 OpenAI 兼容客户端（api_key 可填任意非空占位，本地一般不校验）；
        2. 用 scraper 拉取并截断网页文本（控制上下文窗口用量）；
        3. 调用 chat.completions.create，把 messages 送给模型；
        4. 从返回结构中取出第一条 choice 的 message.content。
    """
    ollama = OpenAI(base_url=OLLAMA_BASE_URL, api_key='ollama')
    # 网页 → 纯文本（内部已截断到约 2000 字符，避免撑爆上下文窗口）
    website = fetch_website_contents(url)
    response = ollama.chat.completions.create(
        model=MODEL,
        messages=messages_for(website)
    )
    return response.choices[0].message.content


def main():
    """
    命令行入口：询问 URL，打印抓取并摘要的结果。

    方便本地快速试跑；笔记本课程里通常会直接调用 summarize()。
    """
    url = input("Enter a URL to summarize: ")
    print("\nFetching and summarizing...\n")
    summary = summarize(url)
    print(summary)


# 仅当直接运行本文件时执行 main()；被 import 时不会自动跑
if __name__ == "__main__":
    main()
