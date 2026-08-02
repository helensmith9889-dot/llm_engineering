# 中文注释版：下方为便于小白阅读的中文旁注；逻辑与标识符未改。
"""
RAG 练习的配置。没有.env；假设奥拉玛正在跑步。

Configuration for RAG exercise. No .env; Ollama is assumed running.
"""

EMBEDDING_MODEL = "nomic-embed-text:v1.5"
LLM_MODEL = "ollama/granite4:tiny-h"

# Chunking (LLM output constraints)
CHUNK_MAX_CHARS = 400
CHUNK_OVERLAP_CHARS = 50

# Retrieval
RETRIEVAL_K = 20  # per query
FINAL_K = 10  # after rerank

FAISS_INDEX_DIR = "faiss_index"
