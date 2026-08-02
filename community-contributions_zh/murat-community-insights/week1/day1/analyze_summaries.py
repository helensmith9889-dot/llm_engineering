"""分析总结的社区贡献并提取生态系统见解。

这个脚本：
1.加载summary_contributions.py生成的项目摘要
2. 将它们发送给法学硕士进行更高层次的分析
3. 将见解保存到 results/ecosystem_insights.md"""
from dotenv import load_dotenv
import json
from pathlib import Path
from openai import OpenAI
import os

# --------------------------------------------------
# 配置
# --------------------------------------------------
# 从项目根加载.env
load_dotenv(Path(__file__).resolve().parents[4] / ".env")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

BASE_DIR = Path(__file__).parent
RESULTS_DIR = BASE_DIR / "results"

INPUT_FILE = RESULTS_DIR / "community_contribution_summaries.json"
OUTPUT_FILE = RESULTS_DIR / "ecosystem_insights.md"

client = OpenAI()


# --------------------------------------------------
# 负载摘要
# --------------------------------------------------

def load_summaries():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            "Summaries file not found. Run summarize_contributions.py first."
        )

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------
# 为 LLM 构建文本输入
# --------------------------------------------------

def build_summary_text(data, limit=80):
    """将项目摘要合并到一个文本块中。
    限制以避免令牌溢出。"""

    summaries = "\n\n".join(
        f"{item['project_name']}:\n{item['summary']}"
        for item in data[:limit]
    )

    return summaries


# --------------------------------------------------
# 生成生态系统见解
# --------------------------------------------------

def analyze_projects(summary_text):

    system_prompt = """
You analyze collections of GitHub community projects.

Your goal is to extract ecosystem insights.

Identify:
- recurring project themes
- interesting or unique projects
- beginner-friendly projects
- commonly used technologies
"""用户提示=f"""
Analyze the following community contribution summaries.

Return:

1. Overall ecosystem summary
2. Top recurring project themes
3. Most interesting or innovative projects
4. Beginner-friendly projects
5. Common technologies used across projects

Data:

{summary_text}
