#!/usr/bin/env python3
"""
将 community-contributions_zh 中的作品按课程周次归类到「按周浏览/」。
用符号链接指向原位置，不移动、不复制大文件（避免破坏现有结构）。
"""
from __future__ import annotations

import os
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # community-contributions_zh
BY_WEEK = ROOT / "按周浏览"
SKIP_TOP = {
    "README.md",
    "00_索引.md",
    "_tools",
    "按周浏览",
}

# 路径/文件名上的周次
WEEK_IN_NAME = [
    (re.compile(r"第\s*([1-8])\s*周", re.I), None),
    (re.compile(r"week\s*[-_]?([1-8])\b", re.I), None),
    (re.compile(r"\bw\s*([1-8])[_-]?(?:day|exercise|ex|lab|sol)", re.I), None),
    (re.compile(r"\bw([1-8])_", re.I), None),
]

# 主题关键词 → 周（小写匹配相对路径）
TOPIC_WEEK: list[tuple[re.Pattern[str], int]] = [
    # week8 agents
    (re.compile(r"(price.?is.?right|planning.?agent|scanner.?agent|ensemble.?agent|messaging.?agent|autonomous.?planning|deal.?agent|modal)", re.I), 8),
    # week7 finetune
    (re.compile(r"(lora|qlora|peft|微调|fine[-_ ]?tun)", re.I), 7),
    # week6 pricing / data
    (re.compile(r"(pricer|定价|xgboost|synthetic.?data|合成数据)", re.I), 6),
    # week5 RAG
    (re.compile(r"\brag\b|chroma|vector.?db|知识库|knowledge[-_ ]?base|retriev|embedding|向量", re.I), 5),
    # week4 code gen
    (re.compile(r"(code.?generat|代码生成|chudnovsky|gauss.?legendre)", re.I), 4),
    # week3 HF / meeting
    (re.compile(r"(huggingface|hf.?pipeline|tokenizer|会议纪要|meeting.?minut|whisper|colab)", re.I), 3),
    # week2 UI / chatbot
    (re.compile(r"(gradio|chatbot|聊天机器人|airline|航空助手|工具调用|tool.?call)", re.I), 2),
    # week1 scrape / summary / brochure
    (re.compile(r"(scraper|selenium|playwright|summar|摘要|brochure|宣传册|ollama|网页抓取|website.?summar)", re.I), 1),
]

# dayN 单独出现时的弱启发（课程：week1 有 day1/2/4/5；很多社区 day1=week1）
DAY_HINT = re.compile(r"(?:^|[/_\-])(?:第\s*)?([1-5])\s*天|(?:^|[/_\-])day\s*([1-5])(?:\b|[_/\-])", re.I)


def weeks_from_text(text: str) -> set[int]:
    found: set[int] = set()
    for rx, _ in WEEK_IN_NAME:
        for m in rx.finditer(text):
            found.add(int(m.group(1)))
    for rx, week in TOPIC_WEEK:
        if rx.search(text):
            found.add(week)
    return found


def classify_path(rel: str) -> set[int]:
    weeks = weeks_from_text(rel)
    if weeks:
        return weeks
    # 弱启发：仅 day1 → week1；day2 可能 week1 或 week2，标为两边？只标 week1 太偏。
    # 若只有 dayN 无 week：day1→1；其余进未分类由上层处理
    m = DAY_HINT.search(rel)
    if m:
        day = int(m.group(1) or m.group(2))
        if day == 1:
            return {1}
    return set()


def safe_link(target: Path, link: Path) -> None:
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.exists() or link.is_symlink():
        link.unlink()
    os.symlink(os.path.relpath(target, start=link.parent), link)


def main() -> None:
    # 清空旧的按周浏览（只删链接树）
    if BY_WEEK.exists():
        for p in sorted(BY_WEEK.rglob("*"), reverse=True):
            if p.is_symlink() or p.is_file():
                p.unlink()
            elif p.is_dir():
                try:
                    p.rmdir()
                except OSError:
                    pass
    for w in range(1, 9):
        (BY_WEEK / f"week{w}").mkdir(parents=True, exist_ok=True)
    (BY_WEEK / "跨周合集").mkdir(parents=True, exist_ok=True)
    (BY_WEEK / "未分类").mkdir(parents=True, exist_ok=True)

    # 统计：顶层条目 → weeks；同时把「带明确周次的文件」链到对应 week
    top_weeks: dict[str, set[int]] = {}
    file_week_links: list[tuple[Path, int, str]] = []  # (src, week, link_name)
    stats = defaultdict(int)

    for top in sorted(ROOT.iterdir(), key=lambda p: p.name.lower()):
        if top.name in SKIP_TOP or top.name.startswith("."):
            continue
        if top.name.endswith(".txt") and top.name.startswith(".batch"):
            continue

        # 收集该顶层下所有相对路径文本
        rels: list[str] = [top.name]
        files: list[Path] = []
        if top.is_file():
            files = [top]
        else:
            for f in top.rglob("*"):
                if f.is_file() and "_tools" not in f.parts:
                    files.append(f)
                    rels.append(str(f.relative_to(ROOT)))

        entry_weeks: set[int] = set()
        for rel in rels:
            entry_weeks |= classify_path(rel)

        # 对每个文件单独再判一次，精确挂到 week
        for f in files:
            rel = str(f.relative_to(ROOT))
            fw = classify_path(rel)
            if not fw:
                continue
            for w in fw:
                # 链接名：贡献者_原文件名，避免冲突
                link_name = f"{top.name}__{f.name}" if top.is_dir() else f.name
                file_week_links.append((f, w, link_name))

        top_weeks[top.name] = entry_weeks

        # 顶层入口链接
        if len(entry_weeks) == 0:
            dest_dir = BY_WEEK / "未分类"
            stats["uncat_top"] += 1
        elif len(entry_weeks) == 1:
            w = next(iter(entry_weeks))
            dest_dir = BY_WEEK / f"week{w}"
            stats[f"week{w}_top"] += 1
        else:
            dest_dir = BY_WEEK / "跨周合集"
            stats["multi_top"] += 1
            # 同时也在各相关 week 下放一份入口链接（方便按周逛）
            for w in sorted(entry_weeks):
                link = BY_WEEK / f"week{w}" / f"_合集入口__{top.name}"
                safe_link(top, link)
                stats[f"week{w}_portal"] += 1

        safe_link(top, dest_dir / top.name)

    # 文件级周链接（便于在 week 目录直接打开 notebook）
    for src, w, link_name in file_week_links:
        link = BY_WEEK / f"week{w}" / "_文件" / link_name
        try:
            safe_link(src, link)
            stats[f"week{w}_files"] += 1
        except OSError:
            stats["link_errors"] += 1

    # 写各周 README
    week_titles = {
        1: "第1周：API / 网页抓取 / 摘要 / 宣传册",
        2: "第2周：Gradio / Chatbot / 工具调用",
        3: "第3周：开源模型 / HF / Colab / 会议纪要",
        4: "第4周：代码生成",
        5: "第5周：RAG 检索增强",
        6: "第6周：定价数据 / 基线模型",
        7: "第7周：微调 Fine-tuning",
        8: "第8周：多智能体 / Price is Right",
    }

    index_lines = [
        "# 按周浏览索引",
        "",
        "本目录用**符号链接**指向 `community-contributions_zh` 内原作品，不占双倍磁盘。",
        "",
        "| 周次 | 主题 | 顶层作品数 | 文件快捷链 |",
        "|------|------|------------|------------|",
    ]

    for w in range(1, 9):
        week_dir = BY_WEEK / f"week{w}"
        tops = [p for p in week_dir.iterdir() if p.name != "_文件" and not p.name.startswith(".")]
        files_dir = week_dir / "_文件"
        n_files = len(list(files_dir.iterdir())) if files_dir.exists() else 0
        title = week_titles[w]
        (week_dir / "README.md").write_text(
            f"# week{w} — {title}\n\n"
            f"- 本目录下条目为符号链接，指向社区贡献中文副本。\n"
            f"- `_文件/`：从路径/文件名识别出属于本周的 notebook/脚本快捷方式。\n"
            f"- `_合集入口__*`：跨周贡献者在本周的入口。\n\n"
            f"**顶层链接数：** {len(tops)}  \n"
            f"**文件快捷链：** {n_files}\n",
            encoding="utf-8",
        )
        index_lines.append(f"| [week{w}](week{w}/) | {title} | {len(tops)} | {n_files} |")

    multi = list((BY_WEEK / "跨周合集").iterdir())
    uncat = list((BY_WEEK / "未分类").iterdir())
    index_lines += [
        "",
        f"- [跨周合集](跨周合集/)：{len(multi)} 个（同一作者/项目跨多周）",
        f"- [未分类](未分类/)：{len(uncat)} 个（名称无法可靠判断周次，可按主题自行浏览）",
        "",
        "## 分类规则（简）",
        "",
        "1. 路径/文件名含 `第N周` / `weekN` → 归入对应周",
        "2. 主题关键词：摘要/爬虫→1，Gradio/Chatbot→2，HF/会议→3，代码生成→4，RAG→5，定价→6，微调→7，Agent→8",
        "3. 命中多周 → `跨周合集`，并在相关 week 放 `_合集入口__`",
        "4. 都未命中 → `未分类`",
        "",
    ]
    (BY_WEEK / "README.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")

    (BY_WEEK / "跨周合集" / "README.md").write_text(
        "# 跨周合集\n\n这些贡献者目录内含多个周次的练习/项目。也可在各 `weekN/` 下找 `_合集入口__*`。\n",
        encoding="utf-8",
    )
    (BY_WEEK / "未分类" / "README.md").write_text(
        "# 未分类\n\n未能从文件名/路径可靠判断周次的作品。可打开后根据内容自行归类；欢迎后续改进分类脚本。\n",
        encoding="utf-8",
    )

    print("DONE")
    for k in sorted(stats):
        print(f"  {k}: {stats[k]}")
    print(f"  multi_dir_entries: {len(multi)}")
    print(f"  uncat_dir_entries: {len(uncat)}")


if __name__ == "__main__":
    main()
