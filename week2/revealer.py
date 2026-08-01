"""
第 2 周辅助模块：在 Jupyter/IPython 中“逐步显现” SVG 图形。

本周与 LLM 工程的关系：
- 模型有时会输出 SVG（矢量图代码）作为可视化结果；
- 本模块不负责 HTTP 抓取，而是把 SVG 字符串加工后在笔记本里动画展示；
- 帮助你观察 LLM 生成的图形元素如何一段段绘制出来，便于调试与演示。

教学提示：若 SVG 来自网页或模型输出，仍可能先经过 scraper / prompt 流水线得到文本。
"""

import xml.etree.ElementTree as ET
from IPython.display import display, SVG


def tag(el):
    """
    取出 XML/SVG 元素的本地标签名（去掉命名空间前缀）。

    参数：
        el: ElementTree 元素节点。

    返回：
        str: 例如把 "{http://www.w3.org/2000/svg}path" 变成 "path"。

    为什么需要：
        SVG 常带默认命名空间，el.tag 会是带花括号的完整名；
        比较时可绘制类型时，用本地名更方便。
    """
    return el.tag.split("}", 1)[-1]


def reveal(svg):
    """
    给 SVG 中可绘制图形加上依次淡入动画，并在笔记本中显示。

    参数：
        svg: SVG 文档的字符串；若为空/假值则什么也不做。

    返回：
        None（副作用：调用 IPython.display 渲染动画 SVG）。

    工作原理（简化）：
        1. 解析 SVG XML；
        2. 注入 CSS @keyframes，定义 .reveal 从透明到不透明；
        3. 遍历 path/line/圆/矩形等可绘制标签，依次设置递增的 animation-delay；
        4. 用 display(SVG(...)) 在单元格输出区展示。
    """
    if svg:
        # 注册默认 SVG 命名空间，序列化时前缀更干净
        ET.register_namespace("", "http://www.w3.org/2000/svg")

        root = ET.fromstring(svg)
        # 这些标签对应“看得见的笔画/形状”，才需要加揭示动画
        drawable = {"path", "line", "ellipse", "rect", "polygon", "polyline", "circle"}
        # 在根节点下插入 <style>，定义 reveal 关键
        style = ET.SubElement(root, "style")
        style.text = """
        @keyframes reveal { from { opacity: 0; } to { opacity: 1; } }
        .reveal { opacity: 0; animation: reveal 0.002s linear forwards; }
        """

        # delay：每个图形比上一个晚 0.15 秒开始显现，形成“一笔一笔画出”的效果
        delay = 0.0
        for el in root.iter():
            if tag(el) in drawable:
                existing = el.get("style", "")
                # 在原有 style 后追加 animation-delay（保留已有样式）
                el.set("style", f"{existing};animation-delay:{delay:.1f}s")
                # 加上 CSS class "reveal"，触发上面定义的动画
                el.set("class", (el.get("class", "") + " reveal").strip())
                delay += 0.15

        # 把改写后的 SVG 树序列化回字符串，交给 IPython 显示
        display(SVG(ET.tostring(root, encoding="unicode")))
