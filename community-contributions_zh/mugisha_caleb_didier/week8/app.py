"""NewsHound - 自主多代理技术新闻情报系统

一个可投入生产的代理人工智能系统，可监控科技新闻源并进行分析
使用 RAG + Modal ML 评分 + Frontier LLM 的文章重要性，并发送
通过 Pushover 推送重要故事的通知。

运行：uv run Community-contributions/mugisha_caleb_didier/week8/app.py"""

import os
import logging
import queue
import threading
import time
import gradio as gr
from framework import NewsFramework, reformat
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=True)

SCAN_INTERVAL = int(os.getenv("NEWSHOUND_INTERVAL", "300"))

HEADER_HTML = """
<div style="text-align:center; padding:10px 0 2px 0;">
    <h1 style="margin:0; font-size:30px; letter-spacing:1px; color:#e0e0e0;">
        <span style="color:#00dddd;">News</span>Hound
    </h1>
    <p style="color:#777; margin:4px 0 0; font-size:13px;">
        Autonomous multi-agent tech news intelligence system
    </p>
</div>
"""def make_stats_html（故事，警报，kb_size，last_scan =“”）：
    def 卡（值、标签、颜色）：
        返回（
            '<div style="背景:rgba(26,26,46,0.85);边框半径:8px;'
            '内边距：14px 24px；文本对齐：居中；最小宽度：110px；边框：1px 实心 #333;">'
            f'<div style="color:{color}; font-size:26px; font-weight:bold;">{value}</div>'
            f'<div style="color:#777; font-size:11px; margin-top:2px;">{label}</div>'
            “</div>”
        ）

    返回（
        '<div style="display:flex; 间隙:12px; justify-content:center; margin:2px 0 6px 0;">'
        + 卡（故事，“找到的故事”，“#00dddd”）
        + 卡（警报，“警报已发送”，“#00dd00”）
        + 卡(kb_size, "知识库", "#dddd00")
        + 卡（last_scan 或“--:--”、“上次扫描”、“#ff7800”）
        +“</div>”
    ）


管道_HTML ="""
<div style="background:rgba(26,26,46,0.85); border-radius:8px; padding:14px 16px;
            border:1px solid #333;">
    <div style="color:#e0e0e0; font-size:14px; font-weight:600; margin-bottom:10px;">
        Agent Pipeline
    </div>
    <table style="width:100%; font-size:12px; line-height:2.2;">
        <tr>
            <td style="color:#00dddd; font-weight:600; width:95px; padding-left:4px;">Scanner</td>
            <td style="color:#888;">RSS feeds + Structured Outputs (Pydantic)</td>
        </tr>
        <tr>
            <td style="color:#4488ff; font-weight:600; padding-left:4px;">Knowledge</td>
            <td style="color:#888;">ChromaDB RAG + SentenceTransformer</td>
        </tr>
        <tr>
            <td style="color:#dddd00; font-weight:600; padding-left:4px;">Analysis</td>
            <td style="color:#888;">GPT-4.1-mini + Modal relevance scorer</td>
        </tr>
        <tr>
            <td style="color:#00dd00; font-weight:600; padding-left:4px;">Planning</td>
            <td style="color:#888;">Autonomous GPT tool calling</td>
        </tr>
        <tr>
            <td style="color:#87CEEB; font-weight:600; padding-left:4px;">Messenger</td>
            <td style="color:#888;">Pushover push notifications + LLM copy</td>
        </tr>
    </table>
</div>
