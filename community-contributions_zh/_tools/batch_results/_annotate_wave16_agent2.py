#!/usr/bin/env python3
"""Teaching-annotate wave16-agent2: steve week1 notebooks. Source-only edits."""
from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path("/home/dev/code/llm_engineering/community-contributions_zh")

# ---------------------------------------------------------------------------
# 1) steve/第1周作业解答.ipynb
# ---------------------------------------------------------------------------
HW = [
    # cell 0
    '''# ========== 导入：把后面要用的工具箱搬进来 ==========

# 从 dotenv 导入 load_dotenv：把 .env 里的密钥读进环境变量（Environment Variables），避免把密钥写进代码
from dotenv import load_dotenv
# 导入标准库 os：读环境变量，例如 OPENAI_API_KEY
import os
# 从 openai 导入 OpenAI 客户端类：既可调云端 Chat Completions，也可指向本地 Ollama 的 OpenAI 兼容端点
from openai import OpenAI
# 从 IPython.display 导入展示工具：Markdown 渲染、display 首次显示、update_display 流式刷新（本格导入备用）
from IPython.display import Markdown, display, update_display

''',
    # cell 1
    '''# ========== 常量：模型名与本地地址集中写在一处 ==========

# OpenAI 云端小模型 id：字符串必须和 API 接受的模型名一致，不要改写
MODEL_GPT = 'gpt-4o-mini'
# 本地 Ollama 模型名：需事先 ollama pull llama3.2
MODEL_LLAMA = 'llama3.2'
# Ollama 的 OpenAI 兼容 Base URL（/v1）；后面用 OpenAI SDK 指向这里即可调本地模型
OLLAMA_BASE_URL = "http://localhost:11434/v1"
''',
    # cell 2
    '''# ========== 环境准备：加载密钥、创建两个客户端、校验 API Key、定义 system prompt ==========

# 加载 .env：override=True 表示用文件里的值覆盖已存在的环境变量
load_dotenv(override=True)
# 默认 OpenAI 客户端：密钥从环境变量 OPENAI_API_KEY 自动读取
openai = OpenAI()
# 第二个客户端指向本地 Ollama；api_key='ollama' 只是占位（本地端点通常不校验真实密钥）
ollama = OpenAI(base_url=OLLAMA_BASE_URL, api_key='ollama')
# 默认选用的模型名常量（本练习后续显式传 MODEL_GPT / MODEL_LLAMA，此变量可作对照）
MODEL = MODEL_LLAMA
# 从环境变量取出 OpenAI API Key，便于做形态检查
api_key = os.getenv('OPENAI_API_KEY')

# 粗查密钥：是否存在、是否以 sk-proj- 开头、长度是否够（启发式，不是官方校验）
if api_key and api_key.startswith('sk-proj-') and len(api_key)>10:
    # 运行时提示字符串保持英文原样（影响行为的可运行文案不翻译）
    print("API key looks good so far")
else:
    print("There might be a problem with your API key? Please visit the troubleshooting notebook!")
    


# system prompt：发给模型的角色/格式指令；必须保留英文原文，改译会改变回答风格
system_prompt = """
You are a seasoned engineer helping users
understand technical problems by using well defined explanations; when a 
question involves code, include the original code 
in a properly formatted markdown code block and provide
a clear, concise explanation of what the code does and
why it is used, ensuring all responses are structured 
and written in markdown format.
"""
''',
    # cell 3
    '''# ========== 核心函数：流式调用 Chat Completions，边收边刷新 Markdown ==========

def theExplainer(question, model, llm):
    # 向传入的 llm 客户端发起流式聊天：model 决定用哪个模型；messages 含 system + user
    stream = llm.chat.completions.create(
    model=model,
    messages=[{"role": "system", "content": system_prompt}, 
    {"role": "user", "content": question}],
    # stream=True：不要等整段生成完，而是持续返回增量 delta
    stream=True)
    # response：累积已收到的全部文本，用于每次刷新完整 Markdown
    response=""
    # display_id=True：拿到可更新的显示句柄，后面用 .update 原地刷新，而不是不断新打一段
    display_handle = display(Markdown(""), display_id=True)
    # 逐块遍历流式响应
    for chunk in stream:
        # delta.content 可能为 None（例如结束标记）；用 or '' 避免把 None 拼进去
        response += chunk.choices[0].delta.content or ''
        # 用当前完整 response 刷新笔记本里的 Markdown 显示
        display_handle.update(Markdown(response))
''',
    # cell 4
    '''# ========== 提问：改这里的字符串就能问新问题 ==========

# 用户问题（user message）保持英文：这是发给模型的内容，翻译会改变任务语义
# 练习建议：换成你自己看不懂的一行代码，再分别跑下面 GPT / Llama 两格做对比
question = """
Please explain what this code does and why:
yield from {book.get("author") for book in books if book.get("author")}
"""
''',
    # cell 5
    '''# ========== 用云端 gpt-4o-mini 流式解答 ==========

# 传入 OpenAI 云端客户端 openai，以及模型常量 MODEL_GPT
theExplainer(question, MODEL_GPT, openai)
''',
    # cell 6
    '''# ========== 用本地 Llama 3.2（经 Ollama OpenAI 兼容端点）流式解答 ==========

# 传入指向本地的 ollama 客户端，以及模型常量 MODEL_LLAMA；可对比两边回答风格
theExplainer(question, MODEL_LLAMA, ollama)
''',
]

# ---------------------------------------------------------------------------
# 2) steve/第1周第1天任务.ipynb  — OpenAI 抓取电商页并抽取商品
# ---------------------------------------------------------------------------
DAY1 = '''# ========== 第 1 天任务：抓取电商页 → 用 GPT 抽取目标商品列表 ==========
# 练习目标：把「网页抓取 + Chat Completions」串起来，按商品名筛出带价格的列表（Markdown 输出）
# 怎么跑：准备好 .env（OPENAI_API_KEY）后，从上到下运行；末尾可改 URL / 商品名再试

# 导入标准库 os：读环境变量（本格主要靠 OpenAI 默认读 OPENAI_API_KEY）
import os
# 从 dotenv 导入 load_dotenv：把 .env 里的密钥读进进程环境，避免把密钥写进代码
from dotenv import load_dotenv
# 从 IPython.display 导入 Markdown / display：在笔记本里漂亮展示模型返回的 Markdown
from IPython.display import Markdown, display
# 从 openai 导入 OpenAI 客户端：调用云端 Chat Completions API
from openai import OpenAI
# 从 bs4 导入 BeautifulSoup：解析 HTML，去掉无关标签后抽出纯文本
from bs4 import BeautifulSoup
# 导入 requests：用 HTTP GET 下载目标网页
import requests


# 浏览器风格 User-Agent：很多网站会拒无头爬虫；字符串保持原样（影响请求是否成功）
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
}

# 加载 .env 到环境变量
load_dotenv()
# 创建默认 OpenAI 客户端（密钥来自环境变量 OPENAI_API_KEY）
openai = OpenAI()



# system prompt：角色 + 抽取规则 + 输出格式；必须保留英文原文，改译会改变模型行为
system_prompt = """You are an AI product extraction assistant.

Your task is to analyze raw scraped e-commerce website content and extract structured product listings that match a specified product name provided by the user.

You will be given:

1. The scraped website content (HTML or text)
2. A target product name

Instructions:

* Identify all products in the content that match or are closely related to the target product name.

* Ignore text that may be navigation related, including menus, headers, footers, category links, breadcrumbs, filters, login sections, advertisements, or pagination elements.

* Focus only on actual product listing information.

* Extract at least 10 relevant product listings where available.

* For each product extract:

  * Product Name
  * Product Description
  * Product Price

Data Handling Rules:

* Ignore listings that do not contain a visible price.
* Normalize all prices into numeric values (remove currency symbols).
* If a price is given as a range, use the higher value.
* Ignore advertisements or unrelated products.

Sorting Rules:
* Sort the final list strictly on price and quality.


Output Format:

Respond in markdown.
Do not wrap the markdown in a code block - respond just with the markdown.

Return the result as a Markdown that includes Product Name Description and Price 

Order in ascending order with the lowest price at the top
Provide a summary after the table of the most recomended as per the price.

* The result must contain at least 10 products where available.
* Prices must be shown as numeric values with currency.

 """
# user prompt 前缀：后面会拼接「网页正文 + 目标商品名」；英文原文保留
user_prompt = """
 Here is the website content and the product name

"""

def fetch_website_contents(url):
    """抓取 url 对应页面，清洗 HTML 后返回「标题 + 正文」截断文本（最多约 2000 字符）。"""
    # GET 目标页；带上 headers 降低被拒概率
    response = requests.get(url, headers=headers)
    # 用 html.parser 解析响应字节为 DOM
    soup = BeautifulSoup(response.content, "html.parser")
    # 取 <title> 文本；没有标题就用占位英文串（字符串保持原样）
    title = soup.title.string if soup.title else "No title found"
    if soup.body:
        # 删掉 script/style/img/input 等对摘要无用的节点，减少噪声
        for irrelevant in soup.body(["script", "style", "img", "input"]):
            irrelevant.decompose()
        # 从 body 抽出可见文本；换行分隔并去掉首尾空白
        text = soup.body.get_text(separator="\\n", strip=True)
    else:
        # 没有 body 时正文为空串
        text = ""
    # 标题与正文用空行拼接，再截断到 2000 字符，控制发给模型的上下文长度
    return (title + "\\n\\n" + text)[:2_000]


def messages_for(website, product_name):
    """组装 Chat Completions 所需的 messages：system 定规则，user 放网页内容 + 商品名。"""
    return [
        {"role": "system", "content": system_prompt},
        # user 内容 = 前缀 + 抓取文本 + 目标商品名（拼接方式保持原样）
        {"role": "user", "content": user_prompt + website+ product_name}
    ]


def summarize(url, product_name):
    """抓取网页 → 调 gpt-4.1-mini → 返回模型生成的 Markdown 字符串。"""
    # 先拿到清洗后的网站文本
    website = fetch_website_contents(url)
    # 非流式 Chat Completions：等整段答完再取 content
    response = openai.chat.completions.create(
        model = "gpt-4.1-mini",
        messages = messages_for(website, product_name)
    )
    # 取第一条 choice 的消息正文
    return response.choices[0].message.content

def display_summary(url, product_name):
    """调用 summarize，并在笔记本里用 Markdown 渲染结果。"""
    summary = summarize(url, product_name)
    display(Markdown(summary))    


# 入口示例：抓 amazon.com，目标商品名为 static bikes（URL / 查询串保持原样）
display_summary("https://amazon.com", "static bikes")
'''

# ---------------------------------------------------------------------------
# 3) steve/第1周第2天任务.ipynb  — 同上，但走本地 Ollama llama3.2
# ---------------------------------------------------------------------------
DAY2 = '''# ========== 第 2 天任务：抓取电商页 → 用本地 Ollama（llama3.2）抽取商品 ==========
# 练习目标：Day1 同一套抓取 + messages 流程，把后端从云端 GPT 换成本地 Llama（OpenAI 兼容 /v1）
# 怎么跑：先启动 Ollama 并 pull llama3.2；本机 11434 可访问后，从上到下运行；末尾可改 URL / 商品名

# 导入标准库 os：读环境变量（本练习主要用本地端点，仍保留常见导入习惯）
import os
# 从 dotenv 导入 load_dotenv：把 .env 读进环境（若有其它配置可一并加载）
from dotenv import load_dotenv
# 从 IPython.display 导入 Markdown / display：在笔记本里漂亮展示模型返回的 Markdown
from IPython.display import Markdown, display
# 从 openai 导入 OpenAI 客户端：通过改 base_url 指向本地 Ollama 的 OpenAI 兼容 API
from openai import OpenAI
# 从 bs4 导入 BeautifulSoup：解析 HTML，去掉无关标签后抽出纯文本
from bs4 import BeautifulSoup
# 导入 requests：用 HTTP GET 下载目标网页
import requests


# 浏览器风格 User-Agent：很多网站会拒无头爬虫；字符串保持原样
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
}

# 加载 .env 到环境变量
load_dotenv()
# 仍创建默认 OpenAI 客户端（本格 summarize 走 ollama；保留原代码结构）
openai = OpenAI()



# Ollama 的 OpenAI 兼容 Base URL（/v1）
OLLAMA_BASE_URL = "http://localhost:11434/v1"

# 指向本地 Ollama；api_key='ollama' 为占位密钥（本地端点通常不校验）
ollama = OpenAI(base_url=OLLAMA_BASE_URL, api_key='ollama')

# system prompt：角色 + 抽取规则 + Markdown 表格格式；必须保留英文原文
system_prompt = """You are an AI product extraction assistant.

Your task is to analyze raw scraped e-commerce website content and extract structured product listings that match a specified product name provided by the user.

You will be given:

1. The scraped website content (HTML or text)
2. A target product name

Instructions:

* Identify all products in the content that match or are closely related to the target product name.

* Ignore text that may be navigation related, including menus, headers, footers, category links, breadcrumbs, filters, login sections, advertisements, or pagination elements.

* Focus only on actual product listing information.

* Extract at least 10 relevant product listings where available.

* For each product extract:

  * Product Name
  * Product Description
  * Product Price

Data Handling Rules:

* Ignore listings that do not contain a visible price.
* Normalize all prices into numeric values (remove currency symbols).
* If a price is given as a range, use the higher value.
* Ignore advertisements or unrelated products.

Sorting Rules:
* Sort the final list strictly on price and quality.


Output Format:

Respond in markdown.
Do not wrap the markdown in a code block - respond just with the markdown.

Return the result as a Markdown table with the following columns:

| Product Name | Description | Price |

Order in ascending order with the lowest price at the top
Provide a summary after the table of the most recomended as per the price.

* The table must contain at least 10 products where available.
* Prices must be shown as numeric values with currency.
* Do not include any commentary before or after the table.
 """
# user prompt 前缀：后面拼接网页正文 + 商品名；英文原文保留
user_prompt = """
 Here is the website content and the product name

"""
def fetch_website_contents(url):
    """抓取 url 对应页面，清洗 HTML 后返回「标题 + 正文」截断文本（最多约 2000 字符）。"""
    # GET 目标页；带上 headers 降低被拒概率
    response = requests.get(url, headers=headers)
    # 用 html.parser 解析响应字节为 DOM
    soup = BeautifulSoup(response.content, "html.parser")
    # 取 <title> 文本；没有标题就用占位英文串
    title = soup.title.string if soup.title else "No title found"
    if soup.body:
        # 删掉 script/style/img/input 等对摘要无用的节点
        for irrelevant in soup.body(["script", "style", "img", "input"]):
            irrelevant.decompose()
        # 从 body 抽出可见文本
        text = soup.body.get_text(separator="\\n", strip=True)
    else:
        text = ""
    # 标题 + 正文，截断到 2000 字符，控制本地模型上下文长度
    return (title + "\\n\\n" + text)[:2_000]

def messages_for(website, product_name):
    """组装 messages：system 定规则，user 放网页内容 + 商品名。"""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt + website + product_name}
    ]


def summarize(url, product_name):
    """抓取网页 → 调本地 llama3.2（经 ollama 客户端）→ 返回 Markdown 字符串。"""
    website = fetch_website_contents(url)
    # 注意：这里用的是 ollama 客户端，不是上面的 openai；model id 保持 llama3.2
    response = ollama.chat.completions.create(
        model = "llama3.2",
        messages = messages_for(website, product_name)
    )
    return response.choices[0].message.content

def display_summary(url, product_name):
    """调用 summarize，并在笔记本里用 Markdown 渲染结果。"""
    summary = summarize(url, product_name)
    display(Markdown(summary))    


# 入口示例：抓 amazon.com，目标商品名为 static bikes（与 Day1 对照同一任务、不同后端）
display_summary("https://amazon.com", "static bikes")
'''


def to_lines(src: str) -> list[str]:
    """Notebook source is a list of lines; ensure trailing newline style matches common ipynb."""
    if not src.endswith("\n"):
        src = src + "\n"
    # splitlines(keepends) then ensure last piece ok
    lines = src.splitlines(keepends=True)
    return lines


def set_source(cell: dict, src: str) -> None:
    cell["source"] = to_lines(src)


def strip_comments_and_docstrings(src: str) -> str:
    """Rough logic fingerprint: parse AST and unparse (drops comments)."""
    tree = ast.parse(src)
    # Remove module/class/function docstrings for fairer compare? Keep them — we may add Chinese docstrings.
    # Instead remove Expr(Constant(str)) that are docstrings at start of bodies.
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(getattr(node.body[0], "value", None), ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                node.body = node.body[1:] or [ast.Pass()]
    return ast.dump(tree, include_attributes=False)


def annotate_notebook(rel: str, sources: list[str]) -> None:
    path = ROOT / rel
    nb = json.loads(path.read_text(encoding="utf-8"))
    assert len(nb["cells"]) == len(sources), (rel, len(nb["cells"]), len(sources))

    # Snapshot outputs / execution_count before
    before = [
        (c.get("execution_count"), json.dumps(c.get("outputs", []), ensure_ascii=False), c.get("metadata"))
        for c in nb["cells"]
    ]

    old_logic = []
    for c in nb["cells"]:
        if c["cell_type"] == "code":
            old_logic.append(strip_comments_and_docstrings("".join(c["source"])))
        else:
            old_logic.append(None)

    for cell, src in zip(nb["cells"], sources):
        if cell["cell_type"] != "code":
            raise SystemExit(f"unexpected non-code cell in {rel}")
        # AST check new source
        ast.parse(src)
        set_source(cell, src)

    new_logic = []
    for c in nb["cells"]:
        new_logic.append(strip_comments_and_docstrings("".join(c["source"])))

    for i, (a, b) in enumerate(zip(old_logic, new_logic)):
        if a != b:
            raise SystemExit(f"LOGIC DRIFT {rel} cell {i}\nOLD:\n{a}\nNEW:\n{b}")

    after = [
        (c.get("execution_count"), json.dumps(c.get("outputs", []), ensure_ascii=False), c.get("metadata"))
        for c in nb["cells"]
    ]
    if before != after:
        raise SystemExit(f"outputs/execution_count/metadata changed in {rel}")

    path.write_text(json.dumps(nb, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"OK {rel}")


def main() -> None:
    annotate_notebook("steve/第1周作业解答.ipynb", HW)
    annotate_notebook("steve/第1周第1天任务.ipynb", [DAY1])
    annotate_notebook("steve/第1周第2天任务.ipynb", [DAY2])

    result = {
        "agent": "wave16-agent2",
        "done": [
            "steve/第1周作业解答.ipynb",
            "steve/第1周第1天任务.ipynb",
            "steve/第1周第2天任务.ipynb",
        ],
        "failed": [],
        "sample_for_review": "steve/第1周作业解答.ipynb",
        "notes": (
            "Annotated 3/3. Source-only edits; outputs/execution_count preserved; "
            "prompts/model ids/URLs/print strings untouched. Replaced shallow 小白提示 "
            "with near line-by-line Chinese teaching comments. AST + logic-fingerprint OK."
        ),
    }
    out = ROOT / "_tools/batch_results/wave16_agent2.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
