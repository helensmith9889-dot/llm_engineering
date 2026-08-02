"""汇总所有 GitHub 社区贡献文件夹并将结果保存为 JSON。

这个脚本：
1. 扫描主要社区贡献目录
2. 从每个贡献文件夹中提取可读文本
3. 将内容发送给LLM进行总结
4. 将所有摘要保存到 results/community_contribution_summaries.json"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# --------------------------------------------------
# 从存储库根加载环境变量
# --------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[4]
load_dotenv(REPO_ROOT / ".env")

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found. Check your .env file.")

client = OpenAI(api_key=api_key)

# --------------------------------------------------
# 路径
# --------------------------------------------------
CURRENT_DIR = Path(__file__).parent
RESULTS_DIR = CURRENT_DIR / "results"
OUTPUT_FILE = RESULTS_DIR / "community_contribution_summaries.json"

# 要分析的主源文件夹
BASE_DIR = REPO_ROOT / "community-contributions"

# 跳过你自己的文件夹，这样你就不用总结自己了
EXCLUDED_DIR_NAMES = {"murat-community-insights"}

# --------------------------------------------------
# 迅速的
# --------------------------------------------------
SYSTEM_PROMPT = """
You are an assistant that summarizes GitHub community contribution projects.

Your task:
- summarize each contribution accurately
- identify the likely purpose of the project
- identify likely category
- list main technologies only if clearly visible
- do not invent details
- if evidence is weak, say 'insufficient evidence'

Return in this format:
Title:
Summary:
Category:
Technologies:
Confidence:
"""# --------------------------------------------------
# 从每个项目文件夹中提取有用的文本
# --------------------------------------------------
def extract_project_text(project_dir: 路径) -> str:
    优先级文件 = [
        “自述文件.md”，
        “自述文件.md”，
        “自述文件.MD”，
        “项目.md”，
        “描述.txt”，
    ]

    收集的零件 = []

    # 首先尝试标准描述文件
    对于priority_files中的fname：
        fpath = 项目目录 / fname
        如果 fpath.exists() 和 fpath.is_file()：
            尝试：
                文本= fpath.read_text（编码=“utf-8”，错误=“忽略”）
                如果文本.strip():
                    Collected_parts.append(f"\n--- {fname} ---\n{text[:12000]}")
            除了例外：
                通过

    如果收集零件：
        返回“\n”.join(collected_parts)

    # 回退到一些可读文件
    Fallback_exts = {“.py”，“.ipynb”，“.js”，“.ts”，“.md”，“.txt”}

    对于已排序的 fpath(project_dir.rglob("*"))：
        如果fallback_exts中的fpath.is_file()和fpath.suffix.lower()：
            尝试：
                文本= fpath.read_text（编码=“utf-8”，错误=“忽略”）
                如果文本.strip():
                    Collected_parts.append(f"\n--- {fpath.name} ---\n{text[:4000]}")
            除了例外：
                通过

        如果 len(collected_parts) >= 3:
            打破

    return "\n".join(collected_parts) ifcollected_parts else "未找到可读内容。"

# --------------------------------------------------
# 总结一个项目
# --------------------------------------------------
def summarise_project(project_name: str, project_text: str) -> str:
    用户提示=f"""
Analyze this contribution folder.

Folder name:
{project_name}

Project content:
{project_text}
