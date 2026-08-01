"""
原始 Amazon 元数据 → 结构化 Item 的解析与清洗。

微调定价模型前，「垃圾进、垃圾出」问题尤其致命：价格缺失、型号乱码、
过短描述都会污染训练信号。本模块做价格区间过滤、字段拼接、型号擦除、
重量单位换算，只保留足够信息量的样本。

教学上可对照：这是数据集构建（dataset curation）步骤，发生在任何
tokenization / SFT 之前。
"""

from pricer.items import Item
import json
import re

# 清洗后全文至少这么多字符，否则丢弃（信息太少难学价格）
MIN_CHARS = 600
# 合理价格下界（美元）
MIN_PRICE = 0.5
# 合理价格上界；略小于 1000，过滤极端贵价
MAX_PRICE = 999.49
# 描述/特征等单块文本截断长度
MAX_TEXT_EACH = 3000
# 拼接后全文总长度上限
MAX_TEXT_TOTAL = 4000

# 细节字典里要删除的噪声字段（与价格相关性弱或含干扰编号）
REMOVALS = [
    "Part Number",
    "Best Sellers Rank",
    "Batteries Included?",
    "Batteries Required?",
    "Item model number",
]


def simplify(text_list) -> str:
    """
    把列表/文本压成单行短字符串：去换行制表、压空格，再截到 MAX_TEXT_EACH。

    目的：减少空白噪音，控制进入模型/摘要前的上下文长度。
    """
    return (
        str(text_list)
        .replace("\n", " ")
        .replace("\r", "")
        .replace("\t", "")
        .replace("  ", " ")
        .strip()[:MAX_TEXT_EACH]
    )


def scrub(title, description, features, details) -> str:
    """
    拼出清洗后的全文 full：删无关细节、去类型号的字母数字串，再截断总长。

    正则含义（直观版）：长度≥7、同时含大写字母与数字的「词」——常见 SKU/型号，
    对人类读价帮助有限，却容易让模型死记编号。
    """
    for remove in REMOVALS:
        details.pop(remove, None)
    result = title + "\n"
    if description:
        result += simplify(description) + "\n"
    if features:
        result += simplify(features) + "\n"
    if details:
        result += json.dumps(details) + "\n"
    pattern = r"\b(?=[A-Z0-9]{7,}\b)(?=.*[A-Z])(?=.*\d)[A-Z0-9]+\b"
    return re.sub(pattern, "", result).strip()[:MAX_TEXT_TOTAL]


def get_weight(details):
    """
    从 details['Item Weight'] 解析重量，统一换算为磅（pounds）。

    解析失败或缺失时返回 0。重量可作为额外特征（本周 DNN 未必用到）。
    """
    weight_str = details.get("Item Weight")
    if weight_str:
        parts = weight_str.split(" ")
        amount = float(parts[0])
        unit = parts[1].lower()
        if unit == "pounds":
            return amount
        elif unit == "ounces":
            return amount / 16
        elif unit == "grams":
            return amount / 453.592
        elif unit == "milligrams":
            return amount / 453592
        elif unit == "kilograms":
            return amount / 0.453592
        elif unit == "hundredths" and parts[2].lower() == "pounds":
            return amount / 100
    return 0


def parse(datapoint, category):
    """
    尝试从一条原始 datapoint 构造 Item；不合格返回 None。

    过滤条件：价格可解析且在 [MIN_PRICE, MAX_PRICE]，且 scrub 后文本够长。
    """
    try:
        price = float(datapoint["price"])
    except ValueError:
        return None
    if MIN_PRICE <= price <= MAX_PRICE:
        title = datapoint["title"]
        description = datapoint["description"]
        features = datapoint["features"]
        details = json.loads(datapoint["details"])
        weight = get_weight(details)
        full = scrub(title, description, features, details)
        if len(full) >= MIN_CHARS:
            return Item(
                title=title,
                category=category,
                price=price,
                full=full,
                weight=weight,
            )
