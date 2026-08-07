# 按周浏览索引

本目录用**符号链接**指向 `community-contributions_zh` 内原作品，不占双倍磁盘。

**优先跟做**：同级目录 [`../优质练习/`](../优质练习/)（精选练习 + 为什么优质 / 锻炼点说明）。

## 整理原则（重要）

1. **只保留练习/项目向作品**；与官方 `week1`–`week8` 课内 `day*.ipynb` **高度重合的翻版已删除**（审计见 [`../_tools/lab_copy_deleted.json`](../_tools/lab_copy_deleted.json)）。
2. 官方课内实验请直接打开仓库根目录的 `weekN/day*_zh.ipynb`，不要在社区目录里找「第二份 day1」。
3. 带独特场景/技术的变体（Playwright、JIRA、垂直业务等）会保留，即使从 day 实验改出。

| 周次 | 主题 |
|------|------|
| [week1](week1/) | 第1周：API / 网页抓取 / 摘要 / 宣传册 |
| [week2](week2/) | 第2周：Gradio / Chatbot / 工具调用 |
| [week3](week3/) | 第3周：开源模型 / HF / Colab / 会议纪要 |
| [week4](week4/) | 第4周：代码生成 |
| [week5](week5/) | 第5周：RAG 检索增强 |
| [week6](week6/) | 第6周：定价数据 / 基线模型 |
| [week7](week7/) | 第7周：微调 Fine-tuning |
| [week8](week8/) | 第8周：多智能体 / Price is Right |

- [跨周合集](跨周合集/)：同一作者/项目跨多周
- [未分类](未分类/)：名称无法可靠判断周次

## 分类规则（简）

1. 路径/文件名含 `第N周` / `weekN` → 归入对应周
2. 主题关键词：摘要/爬虫→1，Gradio/Chatbot→2，HF/会议→3，代码生成→4，RAG→5，定价→6，微调→7，Agent→8
3. 命中多周 → `跨周合集`，并在相关 week 放 `_合集入口__`
4. 都未命中 → `未分类`

重新分类可运行：`python3 ../_tools/organize_by_week.py`
