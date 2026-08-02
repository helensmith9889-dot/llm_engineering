# Gmail AI 摘要器
# 使用 OpenAI 的 GPT-4o-mini，汇总今天的 Gmail 邮件。
# 流程：Gmail 鉴权 → 拉取今日邮件 → 提取正文 → 按规则生成简洁摘要。
# 作者：Javid Hussain Fazaeli

import os
import base64
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from dotenv import load_dotenv

from openai import OpenAI

load_dotenv()

# ---------- 配置 ----------
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not found in .env")

client = OpenAI(api_key=OPENAI_API_KEY)

MODEL = "gpt-4o-mini"  # 便宜且适合做摘要


# 系统提示：把邮件压成每日简报
SYSTEM_PROMPT = """You summarize emails into a crisp daily digest.
Rules:
- 1-2 sentences max per email.
- Start with who it's from.
- Include any deadlines, required actions, and links (just mention "has link" if long).
- If it's spam/promotional, label it PROMO and summarize in 1 short line.
- If it's urgent/needs reply, label ACTION REQUIRED.
"""


def get_gmail_service():
    """获取 Gmail API 服务；必要时走 OAuth 并缓存 token.json。"""
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def extract_best_body(payload):
    """
    尽量从 Gmail 消息 payload 中提取可读正文。
    优先 text/plain；必要时回退到 text/html。
    """
    def decode(data):
        return base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="replace")

    mime_type = payload.get("mimeType", "")
    body = payload.get("body", {}).get("data")

    if body:
        return decode(body)

    parts = payload.get("parts", [])
    if not parts:
        return ""

    # 优先纯文本
    for p in parts:
        if p.get("mimeType") == "text/plain" and p.get("body", {}).get("data"):
            return decode(p["body"]["data"])

    # 其次 HTML
    for p in parts:
        if p.get("mimeType") == "text/html" and p.get("body", {}).get("data"):
            return decode(p["body"]["data"])

    # 递归处理嵌套 multipart
    for p in parts:
        if p.get("parts"):
            text = extract_best_body(p)
            if text:
                return text

    return ""


def summarize_email(from_, subject, date_str, body):
    # 保持提示干净、偏 “Ed Donner 风格”（系统规则 + 用户任务）
    user_prompt = f"""Summarize this email for my daily digest.

From: {from_}
Subject: {subject}
Date: {date_str}

Body:
{body[:6000]}  # safety: avoid huge tokens
"""
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    return resp.choices[0].message.content.strip()


def main():
    service = get_gmail_service()

    # Gmail 查询：精确“本地午夜之后”不好写。
    # 最简单：用 newer_than:1d 表示“大概今天”，
    # 或用 after:YYYY/MM/DD（按本地日期）。
    today = datetime.now().strftime("%Y/%m/%d")
    query = f"after:{today}"

    results = service.users().messages().list(userId="me", q=query, maxResults=20).execute()
    msgs = results.get("messages", [])

    if not msgs:
        print("No emails found for today.")
        return

    print(f"Found {len(msgs)} emails for today (query: {query}).\n")

    for i, m in enumerate(msgs, start=1):
        full = service.users().messages().get(userId="me", id=m["id"], format="full").execute()
        headers = full.get("payload", {}).get("headers", [])

        def h(name):
            for x in headers:
                if x.get("name", "").lower() == name.lower():
                    return x.get("value", "")
            return ""

        from_ = h("From")
        subject = h("Subject")
        date_str = h("Date")

        body = extract_best_body(full.get("payload", {})).strip()

        # 可选：正文为空时给占位
        if not body:
            body = "(No body found; likely a short/structured email.)"

        summary = summarize_email(from_, subject, date_str, body)
        print(f"{i}. {summary}\n")


if __name__ == "__main__":
    main()
