"""
招聘启事 → 一页纸：把招聘广告整理成结构化一页纸，方便投递。
支持 URL（抓取）或粘贴文本（如来自 LinkedIn）。
"""
import os
from dotenv import load_dotenv
from openai import OpenAI

from scraper import fetch_website_contents

load_dotenv(override=True)

DEFAULT_MODEL = "openai/gpt-4o-mini"

SYSTEM_PROMPT = """You are a career coach helping a candidate prepare their application.
Given a job posting (full text or excerpt), produce a clear, actionable one-pager in markdown.

Output exactly these sections with these headers. Use bullet points where indicated. Be concise.

## Role summary
2–3 sentences: what the role is, level, and main focus.

## Key requirements
Bullet list of must-have qualifications, skills, or experience from the posting.

## Nice-to-haves
Bullet list of preferred but not mandatory items.

## Suggested cover letter bullets
3–5 short bullet points the candidate could use in a cover letter or "Why I'm a fit" section. Each should tie their experience to the role. Write in first person, ready to paste or lightly edit.

## Keywords to include in resume
Comma-separated list of terms from the posting that should appear on the candidate's resume (skills, tools, methodologies).

Do not wrap the response in a code block. Output only the markdown."""

USER_PROMPT_PREFIX = """Here is the job posting text:

"""


def get_job_text(url_or_text: str) -> str:
    """
    若 url_or_text 看起来像 URL，则抓取并返回页面内容。
    否则原样返回（粘贴的职位文本）。
    """
    s = url_or_text.strip()
    if s.startswith("http://") or s.startswith("https://"):
        return fetch_website_contents(s)
    return s


def generate_one_pager(
    url_or_pasted_text: str,
    *,
    model: str = DEFAULT_MODEL,
) -> str:
    """
    从职位 URL 或粘贴的职位文本生成一页纸。

    - url_or_pasted_text: 职位页 URL，或招聘广告原文。
    - model: 模型名（如 'openai/gpt-4o-mini'、'anthropic/claude-3.5-sonnet'）。
    - client: 可选 OpenAI 客户端（未提供则创建 OpenRouter 客户端）。

    返回 Markdown 字符串形式的一页纸。
    """
    job_text = get_job_text(url_or_pasted_text)
    if not job_text or len(job_text.strip()) < 50:
        return "Error: No meaningful job text. Provide a URL or paste the full job description (at least a few sentences)."

    openai_client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT_PREFIX + job_text},
    ]
    response = openai_client.chat.completions.create(model=model, messages=messages)
    return response.choices[0].message.content or ""


def stream_one_pager(
    url_or_pasted_text: str,
    *,
    model: str = DEFAULT_MODEL,
):
    """
    逐 token 流式生成一页纸（便于在笔记本/UI 中展示）。
    产出文本块。
    """
    job_text = get_job_text(url_or_pasted_text)
    if not job_text or len(job_text.strip()) < 50:
        yield "Error: No meaningful job text. Provide a URL or paste the full job description."
        return

    openai_client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT_PREFIX + job_text},
    ]
    stream = openai_client.chat.completions.create(
        model=model, messages=messages, stream=True
    )
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


def main() -> None:
    """命令行：一个参数 = URL 或粘贴文本；无参数则从 stdin 读取。"""
    import sys

    if len(sys.argv) > 1:
        raw = " ".join(sys.argv[1:]).strip()
    else:
        raw = sys.stdin.read().strip()

    if not raw:
        print("Usage: python -m one_pager <url_or_pasted_text>", file=sys.stderr)
        print("   or: echo 'job text...' | python -m one_pager", file=sys.stderr)
        sys.exit(1)

    result = generate_one_pager(raw)
    print(result)


if __name__ == "__main__":
    main()