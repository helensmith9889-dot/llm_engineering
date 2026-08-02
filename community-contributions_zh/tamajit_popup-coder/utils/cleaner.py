"""中文注释版：逻辑与标识符保持不变，仅增加/翻译注释便于小白阅读。"""
import re

def clean_text(text):
    # 删除奇怪的符号
    text = re.sub(r'[^a-zA-Z0-9\n\s.,:()\-\[\]]', '', text)

    # 规范化换行符
    text = re.sub(r'\n+', '\n', text)

    lines = text.split("\n")
    filtered_lines = []

    for line in lines:
        line = line.strip()

        # 跳过短垃圾
        if len(line) < 5:
            continue

        # 消除用户界面噪音
        if any(word in line.lower() for word in [
            "blog", "editorial", "home", "course", "solve"
        ]):
            continue

        # 仅保留相关内容
        # 如果没有（line.lower() 中的关键字，则 [ 中的关键字
        # “输入”、“输出”、“示例”、“给定”、“返回”、“指针”
        # ]):
        # 继续

        # ✅ 已修复：追加行，而不是行
        filtered_lines.append(line)

    cleaned = "\n".join(filtered_lines)

    return cleaned.strip()