"""中文注释版：逻辑与标识符保持原文，便于 import 与运行。"""
from pathlib import Path
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.messages import SystemMessage, HumanMessage, convert_to_messages
from langchain_core.documents import Document
from dotenv import load_dotenv

load_dotenv(override=True)

MODEL      = "gpt-4.1-nano"
DB_NAME    = str(Path(__file__).parent / "db" / "vector_db")
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
RETRIEVAL_K = 10

SYSTEM_PROMPT = """
You are a technical assistant helping a React freelancer answer questions
about their clients' pinned package versions and tech stacks.
You have access to a registry of clients, each with their exact package
versions, slugs, and architectural notes.
Use the given context to answer questions precisely. When referencing versions,
always be exact. If a client is not in the context, say so.
Context:
{context}
"""def _ensure_vectorstore() -> 色度："""
    Return the vectorstore, running ingestion first if the DB doesn't exist yet.
    """如果不是 Path(DB_NAME).exists():
        print("未找到矢量数据库 - 正在运行摄取...")
        从 db.ingest 导入 fetch_documents、create_chunks、create_embeddings
        文档 = fetch_documents()
        块 = create_chunks(文档)
        创建嵌入（块）
        print("摄取完成")

    返回 Chroma(persist_directory=DB_NAME, embedding_function=embeddings)


矢量存储 = _ensure_矢量存储()
检索器 = vectorstore.as_retriever(search_kwargs={"k": RETRIEVAL_K})
llm = ChatOpenAI(温度=0, model_name=MODEL)


def fetch_context(问题: str) -> 列表[文档]:"""
    Retrieve relevant context documents for a question.
    """返回检索器.调用（问题）


def组合问题（问题：str，历史记录：list [dict] = []）-> str："""
    Combine all the user's messages into a single string.
    """Prior = "\n".join(m["content"] for m in History if m["role"] == "user")
    return (之前 + "\n" + 问题).strip()


def 答案_问题(
    问题：str，历史：list[dict] = []
) -> 元组[str, 列表[文档]]:"""
    Answer the given question with RAG; return the answer and the context documents.
