"""
Week 5 RAG（Retrieval-Augmented Generation，检索增强生成）演示前端。

本模块是 Insurellm 专家助手的 Gradio 聊天界面：用户提问后，调用
implementation.answer 中的 RAG 流水线（retrieval 检索 → LLM 生成），
并在侧栏展示从向量数据库（vector DB）取回的相关文档片段（context）。

在 Week 5 管线中的位置：
  ingest（知识入库）→ vector DB → answer（检索+生成）→ 本 app（交互展示）
评估（evaluation）请使用同目录下的 evaluator.py。
"""

import gradio as gr
from dotenv import load_dotenv

from implementation.answer import answer_question

load_dotenv(override=True)


def format_context(context):
    """
    将检索到的文档列表格式化为 HTML，便于在侧栏展示。

    参数:
        context: LangChain Document 列表，每个文档含 page_content 与 metadata。
                 这些文档来自向量检索（retrieval），是 RAG「增强」生成的依据。

    返回:
        带标题与来源标注的 HTML 字符串。
    """
    result = "<h2 style='color: #ff7800;'>Relevant Context</h2>\n\n"
    for doc in context:
        # metadata['source'] 通常是知识库文件路径，帮助用户核对答案出处
        result += f"<span style='color: #ff7800;'>Source: {doc.metadata['source']}</span>\n\n"
        result += doc.page_content + "\n\n"
    return result


def chat(history):
    """
    Gradio 聊天回调：对最新用户消息做一次完整 RAG 问答。

    流程简述：
      1. 取出最后一条用户消息与之前的对话历史
      2. 调用 answer_question（内部会做 embedding 检索 + LLM 生成）
      3. 把助手回复追加进 history，并格式化检索到的 context 供侧栏显示

    参数:
        history: Gradio messages 格式的对话列表，形如 [{"role": "...", "content": "..."}, ...]

    返回:
        (更新后的 history, 检索上下文的 HTML)
    """
    last_message = history[-1]["content"]
    prior = history[:-1]
    # answer_question 返回 (生成答案, 检索到的 Document 列表)
    answer, context = answer_question(last_message, prior)
    history.append({"role": "assistant", "content": answer})
    return history, format_context(context)


def main():
    """构建并启动 Gradio Blocks：左侧对话，右侧展示检索到的 context。"""

    def put_message_in_chatbot(message, history):
        """先把用户输入写入 chatbot，再由 .then(chat) 触发 RAG 回答。"""
        return "", history + [{"role": "user", "content": message}]

    theme = gr.themes.Soft(font=["Inter", "system-ui", "sans-serif"])

    with gr.Blocks(title="Insurellm Expert Assistant", theme=theme) as ui:
        gr.Markdown("# 🏢 Insurellm Expert Assistant\nAsk me anything about Insurellm!")

        with gr.Row():
            with gr.Column(scale=1):
                chatbot = gr.Chatbot(
                    label="💬 Conversation", height=600, type="messages", show_copy_button=True
                )
                message = gr.Textbox(
                    label="Your Question",
                    placeholder="Ask anything about Insurellm...",
                    show_label=False,
                )

            with gr.Column(scale=1):
                # 侧栏展示 retrieval 结果，便于对照「模型依据了哪些文档」
                context_markdown = gr.Markdown(
                    label="📚 Retrieved Context",
                    value="*Retrieved context will appear here*",
                    container=True,
                    height=600,
                )

        # submit 链式调用：先入队用户消息，再执行 chat（RAG）
        message.submit(
            put_message_in_chatbot, inputs=[message, chatbot], outputs=[message, chatbot]
        ).then(chat, inputs=chatbot, outputs=[chatbot, context_markdown])

    ui.launch(inbrowser=True)


if __name__ == "__main__":
    main()
