"""
Week 5 基础版 RAG（Retrieval-Augmented Generation，检索增强生成）问答模块。

流程：
  1. 把用户问题（可结合对话历史）变成检索查询
  2. 用 embeddings（嵌入向量）在 Chroma 向量数据库（vector DB）中做 similarity search
  3. 取回 top-k 相关文档片段（context / chunks）
  4. 将 context 注入 system prompt，调用 LLM 生成答案

在 Week 5 管线中的位置：
  ingest（implementation/ingest.py 写入 vector_db）→ 本模块检索+生成 → app.py 展示
评估时 evaluation/eval.py 也会调用本模块的 fetch_context / answer_question，保证评测与线上一致。
"""

from pathlib import Path
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.messages import SystemMessage, HumanMessage, convert_to_messages
from langchain_core.documents import Document

from dotenv import load_dotenv


load_dotenv(override=True)

MODEL = "gpt-4.1-nano"
DB_NAME = str(Path(__file__).parent.parent / "vector_db")

# embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
# OpenAIEmbeddings：把文本映射为高维向量；检索时「语义相近」≈「向量距离近」
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
RETRIEVAL_K = 10

SYSTEM_PROMPT = """
You are a knowledgeable, friendly assistant representing the company Insurellm.
You are chatting with a user about Insurellm.
If relevant, use the given context to answer any question.
If you don't know the answer, say so.
Context:
{context}
"""

# 连接已由 ingest 写入的持久化 Chroma 库；embedding_function 必须与入库时一致
vectorstore = Chroma(persist_directory=DB_NAME, embedding_function=embeddings)
retriever = vectorstore.as_retriever()
llm = ChatOpenAI(temperature=0, model_name=MODEL)


def fetch_context(question: str) -> list[Document]:
    """
    对问题做向量检索（retrieval），返回最相关的 Document 列表。

    底层：问题 → embedding → 在 vector DB 中找近邻 → 取回原文 chunks。
    k=RETRIEVAL_K 控制返回条数；条数越多上下文更全，但也可能引入噪声。
    """
    return retriever.invoke(question, k=RETRIEVAL_K)


def combined_question(question: str, history: list[dict] = []) -> str:
    """
    将历史中所有用户消息与当前问题拼成一条检索查询字符串。

    多轮对话时，单独用最后一句可能缺主语；拼上 prior user 内容有助于
    检索到正确主题。注意：生成阶段仍用原始 history + 当前 question。
    """
    prior = "\n".join(m["content"] for m in history if m["role"] == "user")
    return prior + "\n" + question


def answer_question(question: str, history: list[dict] = []) -> tuple[str, list[Document]]:
    """
    用 RAG 回答问题：检索 context → 注入 prompt → LLM 生成。

    参数:
        question: 当前用户问题
        history: 对话历史（messages 格式的 dict 列表）

    返回:
        (答案字符串, 本次检索到的 Document 列表)——后者可供 UI 展示或评估使用。
    """
    # 检索用「拼好的查询」；生成时仍保留完整多轮 messages
    combined = combined_question(question, history)
    docs = fetch_context(combined)
    context = "\n\n".join(doc.page_content for doc in docs)
    system_prompt = SYSTEM_PROMPT.format(context=context)
    messages = [SystemMessage(content=system_prompt)]
    messages.extend(convert_to_messages(history))
    messages.append(HumanMessage(content=question))
    response = llm.invoke(messages)
    return response.content, docs
