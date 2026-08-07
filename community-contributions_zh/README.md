# community-contributions_zh — 社区贡献中文整理版

本目录是 [`community-contributions/`](../community-contributions/) 的**中文学习副本**，方便小白浏览同学作品。

## 推荐入口

1. **[`优质练习/`](优质练习/)**：精选练习型作品 +「为什么优质 / 锻炼什么」（优先跟做）
2. **[`按周浏览/`](按周浏览/)**：按周索引的练习/项目向作品（已剔除与官方 `day*` 高重合的课内翻版）

官方课内实验请用仓库根目录 `week1`–`week8` 的 `day*_zh.ipynb`。

### 按周浏览（全量练习索引）

已按课程周次整理到：**[`按周浏览/`](按周浏览/)**

| 周次 | 主题 |
|------|------|
| [week1](按周浏览/week1/) | API / 网页抓取 / 摘要 / 宣传册 |
| [week2](按周浏览/week2/) | Gradio / Chatbot / 工具调用 |
| [week3](按周浏览/week3/) | 开源模型 / HF / Colab / 会议纪要 |
| [week4](按周浏览/week4/) | 代码生成 |
| [week5](按周浏览/week5/) | RAG 检索增强 |
| [week6](按周浏览/week6/) | 定价数据 / 基线模型 |
| [week7](按周浏览/week7/) | 微调 Fine-tuning |
| [week8](按周浏览/week8/) | 多智能体 / Price is Right |
| [跨周合集](按周浏览/跨周合集/) | 同一作者跨多周 |
| [未分类](按周浏览/未分类/) | 名称无法可靠判断周次 |

说明：`按周浏览/` 里是**符号链接**，指向本目录原作品，不占双倍空间。完整索引见 [`按周浏览/README.md`](按周浏览/README.md)。  
重新分类可运行：`python3 _tools/organize_by_week.py`

## 整理规则

1. **源目录不动**：英文原版仍在 `community-contributions/`。
2. **文本类已翻译 / 加注（教学版标准，进行中）**：
   - `.md`：全文译为简体中文
   - `.ipynb`：Markdown / 理念全中文；代码**逐行教学中文注释**；仅保留可运行英文（标识符、prompt、model id 等）；**不改逻辑、不清空 outputs**。标准见 [`_tools/teaching_annotate_STYLE.md`](_tools/teaching_annotate_STYLE.md)，进度见 [`_tools/teaching_annotate_progress.json`](_tools/teaching_annotate_progress.json)。样板：`abdoul/第1周练习.ipynb`
   - `.py`：加小白向中文注释 / docstring（不改逻辑与标识符）
   - 旧版「浅旁注」正按上述标准加深；未改完的文件仍可能是浅注释
3. **非文本资源**：图片、音频、数据库、锁文件等尽量原样复制（或跳过超大文件）。
4. **命名**：
   - **贡献者人名目录**通常保留原文（如 `Ahmed-Hafez`）
   - **项目型英文文件名**尽量改为中文
   - `.py` 模块文件名若可能被 import，优先保留英文名，只加中文注释
5. **扁平索引**：见 [`00_索引.md`](00_索引.md)（按贡献者条目）。

## 怎么用

1. 学到第 N 周 → 打开 [`按周浏览/weekN/`](按周浏览/) 看同学同周作品找灵感  
2. 想按作者翻 → 看本目录顶层文件夹或 [`00_索引.md`](00_索引.md)  
3. 对照原文 / 提交 PR → 回 [`community-contributions/`](../community-contributions/)  
4. 主课路径 → [`小白向 8 周学习计划（中文材料版）.md`](../小白向%208%20周学习计划（中文材料版）.md)
