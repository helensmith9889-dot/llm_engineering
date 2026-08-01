"""
Week 5 基础版知识入库（ingest）：把 Markdown 知识库写入向量数据库（vector DB）。

RAG（Retrieval-Augmented Generation，检索增强生成）的「离线准备」阶段：
  1. 加载 knowledge-base 下各目录的 .md 文档
  2. Chunking（分块）：用 RecursiveCharacterTextSplitter 切成重叠片段
  3. Embeddings（嵌入）：把每个 chunk 变成向量
  4. 写入 Chroma 持久化目录 vector_db，供 answer.py 在线检索

在 Week 5 管线中的位置：ingest（本文件）→ vector DB → answer → app / evaluation。
运行本脚本一次（或知识库变更后重跑）即可刷新向量库。
"""

import os
import glob
from pathlib import Path
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings


from dotenv import load_dotenv

MODEL = "gpt-4.1-nano"

DB_NAME = str(Path(__file__).parent.parent / "vector_db")
KNOWLEDGE_BASE = str(Path(__file__).parent.parent / "knowledge-base")

# embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

load_dotenv(override=True)

# 与 answer.py 使用同一 embedding 模型，否则检索空间不一致、效果会变差
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")


def fetch_documents():
    """
    从 knowledge-base 各子文件夹加载全部 Markdown 文档。

    每个顶层文件夹名写入 metadata['doc_type']（如 products、employees），
    便于日后按类型过滤；DirectoryLoader 递归匹配 **/*.md。
    """
    folders = glob.glob(str(Path(KNOWLEDGE_BASE) / "*"))
    documents = []
    for folder in folders:
        doc_type = os.path.basename(folder)
        loader = DirectoryLoader(
            folder, glob="**/*.md", loader_cls=TextLoader, loader_kwargs={"encoding": "utf-8"}
        )
        folder_docs = loader.load()
        for doc in folder_docs:
            doc.metadata["doc_type"] = doc_type
            documents.append(doc)
    return documents


def create_chunks(documents):
    """
    将长文档切成带重叠的文本块（chunks）。

    chunk_size=500：单块大约 500 字符，适合作为检索粒度；
    chunk_overlap=200：相邻块重叠，减少「关键信息被切断」导致检索失败的风险。
    RecursiveCharacterTextSplitter：优先按段落/句子边界递归切分，比固定窗口更自然。
    """
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=200)
    chunks = text_splitter.split_documents(documents)
    return chunks


def create_embeddings(chunks):
    """
    为所有 chunks 计算 embeddings 并写入 Chroma 向量库。

    若 DB_NAME 已存在则先 delete_collection，保证全量重建、避免旧数据残留。
    最后打印向量条数与维度（dimensions），便于确认入库成功。
    """
    if os.path.exists(DB_NAME):
        Chroma(persist_directory=DB_NAME, embedding_function=embeddings).delete_collection()

    vectorstore = Chroma.from_documents(
        documents=chunks, embedding=embeddings, persist_directory=DB_NAME
    )

    collection = vectorstore._collection
    count = collection.count()

    # 取一条样本向量，查看 embedding 维度（如 text-embedding-3-large 为高维）
    sample_embedding = collection.get(limit=1, include=["embeddings"])["embeddings"][0]
    dimensions = len(sample_embedding)
    print(f"There are {count:,} vectors with {dimensions:,} dimensions in the vector store")
    return vectorstore


if __name__ == "__main__":
    # 完整 ingest 流水线：加载 → 分块 → 嵌入入库
    documents = fetch_documents()
    chunks = create_chunks(documents)
    create_embeddings(chunks)
    print("Ingestion complete")
