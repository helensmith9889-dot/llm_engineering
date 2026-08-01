"""
Gradio 界面自定义 CSS（教学用）

本文件只导出一个字符串常量 CSS，供 Gradio 的 css= 参数注入。
作用：让「Python ↔ C++」一类本地加速 / 代码转换 Demo 的界面更易读——
用颜色区分语言、统一卡片与按钮风格，而不是改业务逻辑。

概念提示（Gradio + CSS）：
- Gradio 会生成带特定 class 的 HTML；你写的 CSS 通过选择器命中这些 class。
- :root 里用 CSS 变量（--py-color 等）集中管理主题色，改一处即可全局生效。
- !important 在 Gradio 主题样式较「强」时常用，用来盖过默认按钮/容器样式。
- 自定义 class（如 .convert-btn、.py-out）需要在构建 Gradio 组件时
  通过 elem_classes= 挂到对应控件上，CSS 才会生效。
- 本地跑 ML/LLM Demo 时，界面样式与模型无关；本文件不涉及 CUDA/GPU。
"""

# CSS：整段作为 Gradio 自定义样式字符串；内容本身是「样式字面量」，勿改选择器语义
CSS = """
:root {
  --py-color: #209dd7;
  --cpp-color: #ecad0a;
  --accent:   #753991;
  --card:     #161a22;
  --text:     #e9eef5;
}

/* Full-width layout */
.gradio-container {
  max-width: 100% !important;
  padding: 0 40px !important;
}

/* Code card styling */
.card {
  background: var(--card);
  border: 1px solid rgba(255,255,255,.08);
  border-radius: 14px;
  padding: 10px;
}

/* Buttons */
.convert-btn button {
  background: var(--accent) !important;
  border-color: rgba(255,255,255,.12) !important;
  color: white !important;
  font-weight: 700;
}
.run-btn button {
  background: #202631 !important;
  color: var(--text) !important;
  border-color: rgba(255,255,255,.12) !important;
}
.run-btn.py button:hover  { box-shadow: 0 0 0 2px var(--py-color) inset; }
.run-btn.cpp button:hover { box-shadow: 0 0 0 2px var(--cpp-color) inset; }
.convert-btn button:hover { box-shadow: 0 0 0 2px var(--accent) inset; }

/* Outputs with color tint */
.py-out textarea {
  background: linear-gradient(180deg, rgba(32,157,215,.18), rgba(32,157,215,.10));
  border: 1px solid rgba(32,157,215,.35) !important;
  color: rgba(32,157,215,1) !important;
  font-weight: 600;
}
.cpp-out textarea {
  background: linear-gradient(180deg, rgba(236,173,10,.22), rgba(236,173,10,.12));
  border: 1px solid rgba(236,173,10,.45) !important;
  color: rgba(236,173,10,1) !important;
  font-weight: 600;
}

/* Align controls neatly */
.controls .wrap {
  gap: 10px;
  justify-content: center;
  align-items: center;
}
"""
