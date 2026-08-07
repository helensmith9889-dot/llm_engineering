# AGENTS.md — 本仓库协作约定

## 学习 / 解释 → 先问是否落盘

当用户在**学习、解释概念、对照语法、梳理 LLM 知识点**（而不是单纯改代码）时：

1. 先把问题讲清楚。
2. **必须追问一句**：是否需要保存到学习笔记？
3. 用户说要保存 → 按下方路由写入 `python学习笔记/`，风格对齐已有笔记（来源 notebook、小标题、对照表、小练习）。
4. 用户说不保存 → 只口头解释，不写文件。

详细步骤见项目技能：`.cursor/skills/learning-notes/SKILL.md`。

## 笔记路由（`python学习笔记/`）

| 内容类型 | 写入文件 |
|----------|----------|
| Python 基础（import、dict、`.get`、f-string、列表推导等） | [`基础语法.md`](python学习笔记/基础语法.md) |
| 与 JavaScript 的对照（写在同一篇 Python 笔记里） | [`基础语法.md`](python学习笔记/基础语法.md) |
| LLM / Prompt / Tool calling / RAG / 微调等课程概念 | [`llm.md`](python学习笔记/llm.md) |
| Gradio 界面专题（已有独立篇） | [`Gradio.md`](python学习笔记/Gradio.md) |

- 追加为主，不无故整篇重写。
- 新小节注明来源 notebook（如 `week2/day4_zh.ipynb`）。
- 已有更细的专题文件（如 `dict与f-string.md`）可保留；**新的** Python / JS 对照默认写进 `基础语法.md`。
