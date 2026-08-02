"""中文注释版：逻辑与标识符保持原文，便于 import 与运行。"""
import os
import shutil
from pathlib import Path
from langchain_core.documents import Document
from huggingface_hub import snapshot_download
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

load_dotenv(override=True)

MODEL = "gpt-4.1-nano"
DB_NAME = str(Path(__file__).parent / "vector_db")
KNOWLEDGE_BASE = Path(__file__).parent / "knowledge-base"
DOCS_DIR = KNOWLEDGE_BASE / "docs"

embeddings = OpenAIEmbeddings(model="text-embedding-3-large")


def _is_hidden(path: Path, relative_to: Path) -> bool:
    """仅检查隐藏文件/文件夹的相关部分。"""
    return any(part.startswith(".") for part in path.relative_to(relative_to).parts)


def fetch_documents(
    repo_id: str = "mrpeski/frontend-docs",
) -> list[Document]:
    """1.下载HF仓库→保存到知识库/docs/
    2. 从整个knowledge-base/ 目录加载所有.md/.mdx 文件。

    这意味着knowledge-base/下的任何文件夹（例如clients/、docs/）
    被自动摄取。

    元数据[“doc_type”] =知识库/下的顶级文件夹，例如“文档”、“客户”
    元数据[“源”] = 相对路径，例如“文档/next.js/routing/pages.mdx”"""
    print(f"Downloading {repo_id}...")
    local_dir = Path(snapshot_download(repo_id=repo_id, repo_type="dataset"))
    print(f"Cached at: {local_dir}")

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    copied = 0
    for file_path in local_dir.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.suffix not in {".md", ".mdx"}:
            continue
        if _is_hidden(file_path, local_dir):
            continue
        dest = DOCS_DIR / file_path.relative_to(local_dir)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, dest)
        copied += 1
    print(f"Saved {copied} files → {DOCS_DIR}")

    documents = []
    for file_path in KNOWLEDGE_BASE.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.suffix not in {".md", ".mdx"}:
            continue
        if _is_hidden(file_path, KNOWLEDGE_BASE):
            continue
        relative = file_path.relative_to(KNOWLEDGE_BASE)
        doc_type = relative.parts[0]  # e.g. "docs", "clients"
        doc = Document(
            page_content=file_path.read_text(encoding="utf-8", errors="ignore"),
            metadata={
                "doc_type": doc_type,
                "source": str(relative),
            },
        )
        documents.append(doc)

    print(f"Loaded {len(documents)} documents from {KNOWLEDGE_BASE}")
    return documents


def create_chunks(documents: list[Document]) -> list[Document]:
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=200)
    chunks = text_splitter.split_documents(documents)
    print(f"Created {len(chunks)} chunks")
    return chunks


def create_embeddings(chunks: list[Document]) -> Chroma:
    if not chunks:
        raise ValueError("No chunks to embed — check fetch_documents() output.")

    if os.path.exists(DB_NAME):
        Chroma(
            persist_directory=DB_NAME, embedding_function=embeddings
        ).delete_collection()

    print(
        f"Creating embeddings and saving to Chroma. This will take some compute time..."
    )
    vectorstore = Chroma.from_documents(
        documents=chunks, embedding=embeddings, persist_directory=DB_NAME
    )

    collection = vectorstore._collection
    count = collection.count()
    dimensions = len(collection.get(limit=1, include=["embeddings"])["embeddings"][0])
    print(f"{count:,} vectors with {dimensions:,} dimensions in the vector store")

    return vectorstore


if __name__ == "__main__":
    documents = fetch_documents()
    chunks = create_chunks(documents)
    create_embeddings(chunks)
    print("Ingestion complete")

