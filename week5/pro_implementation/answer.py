"""
Week 5 进阶版（pro）RAG（Retrieval-Augmented Generation，检索增强生成）问答模块。

相对基础版 implementation/answer.py，本模块增加常见生产技巧：
  - Query rewriting（查询改写）：把多轮口语问题改成更适合检索的短查询
  - 双路检索：原问题 + 改写问题各自查向量库，再合并（merge）去重
  - Reranking（重排序）：用 LLM 按相关性重排 chunks，只保留 FINAL_K 条
  - 向量库为 Chroma PersistentClient（preprocessed_db，由 pro ingest 写入）

在 Week 5 管线中的位置：
  pro_implementation/ingest → preprocessed_db → 本模块（改写/检索/重排/生成）
评估侧仍可对接同一套 evaluation；本文件侧重更高召回与更准排序。
"""

from openai import OpenAI
from dotenv import load_dotenv
from chromadb import PersistentClient
from litellm import completion
from pydantic import BaseModel, Field
from pathlib import Path
from tenacity import retry, wait_exponential


load_dotenv(override=True)

# MODEL = "openai/gpt-4.1-nano"
MODEL = "groq/openai/gpt-oss-120b"
DB_NAME = str(Path(__file__).parent.parent / "preprocessed_db")
KNOWLEDGE_BASE_PATH = Path(__file__).parent.parent / "knowledge-base"
SUMMARIES_PATH = Path(__file__).parent.parent / "summaries"

collection_name = "docs"
embedding_model = "text-embedding-3-large"
# 指数退避重试：遇限流（rate limit）等短暂失败时自动等待再试
wait = wait_exponential(multiplier=1, min=10, max=240)

openai = OpenAI()

chroma = PersistentClient(path=DB_NAME)
collection = chroma.get_or_create_collection(collection_name)

# 先多取一些（RETRIEVAL_K），重排后再截断到 FINAL_K，兼顾召回与精排
RETRIEVAL_K = 20
FINAL_K = 10

SYSTEM_PROMPT = """
You are a knowledgeable, friendly assistant representing the company Insurellm.
You are chatting with a user about Insurellm.
Your answer will be evaluated for accuracy, relevance and completeness, so make sure it only answers the question and fully answers it.
If you don't know the answer, say so.
For context, here are specific extracts from the Knowledge Base that might be directly relevant to the user's question:
{context}

With this context, please answer the user's question. Be accurate, relevant and complete.
"""


class Result(BaseModel):
    """单条检索结果：正文 page_content + 元数据 metadata（如 source）。"""

    page_content: str
    metadata: dict


class RankOrder(BaseModel):
    """LLM 重排输出：按相关性从高到低排列的 chunk id 列表。"""

    order: list[int] = Field(
        description="The order of relevance of chunks, from most relevant to least relevant, by chunk id number"
    )


@retry(wait=wait)
def rerank(question, chunks):
    """
    用 LLM 对候选 chunks 做重排序（reranking）。

    向量相似度只是近似；LLM 可读全文后给出更贴题的顺序。
    返回按相关性排序后的 Result 列表（id 从 1 起对应输入顺序）。
    """
    system_prompt = """
You are a document re-ranker.
You are provided with a question and a list of relevant chunks of text from a query of a knowledge base.
The chunks are provided in the order they were retrieved; this should be approximately ordered by relevance, but you may be able to improve on that.
You must rank order the provided chunks by relevance to the question, with the most relevant chunk first.
Reply only with the list of ranked chunk ids, nothing else. Include all the chunk ids you are provided with, reranked.
"""
    user_prompt = f"The user has asked the following question:\n\n{question}\n\nOrder all the chunks of text by relevance to the question, from most relevant to least relevant. Include all the chunk ids you are provided with, reranked.\n\n"
    user_prompt += "Here are the chunks:\n\n"
    for index, chunk in enumerate(chunks):
        user_prompt += f"# CHUNK ID: {index + 1}:\n\n{chunk.page_content}\n\n"
    user_prompt += "Reply only with the list of ranked chunk ids, nothing else."
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    response = completion(model=MODEL, messages=messages, response_format=RankOrder)
    reply = response.choices[0].message.content
    order = RankOrder.model_validate_json(reply).order
    # order 中的 id 从 1 开始，转回 0-based 下标
    return [chunks[i - 1] for i in order]


def make_rag_messages(question, history, chunks):
    """
    组装发给生成模型的 messages：system（含检索 context）+ 历史 + 当前问题。

    context 中带上 source，便于模型（与评估）追溯出处。
    """
    context = "\n\n".join(
        f"Extract from {chunk.metadata['source']}:\n{chunk.page_content}" for chunk in chunks
    )
    system_prompt = SYSTEM_PROMPT.format(context=context)
    return (
        [{"role": "system", "content": system_prompt}]
        + history
        + [{"role": "user", "content": question}]
    )


@retry(wait=wait)
def rewrite_query(question, history=[]):
    """
    查询改写（query rewriting）：把用户当前问题改写成更利于检索的短查询。

    多轮对话里用户常说「那个呢」「上面的价格」——改写后补全实体与意图，
    再去做 embedding 检索，通常能提高召回（recall）。
    """
    message = f"""
You are in a conversation with a user, answering questions about the company Insurellm.
You are about to look up information in a Knowledge Base to answer the user's question.

This is the history of your conversation so far with the user:
{history}

And this is the user's current question:
{question}

Respond only with a short, refined question that you will use to search the Knowledge Base.
It should be a VERY short specific question most likely to surface content. Focus on the question details.
IMPORTANT: Respond ONLY with the precise knowledgebase query, nothing else.
"""
    response = completion(model=MODEL, messages=[{"role": "system", "content": message}])
    return response.choices[0].message.content


def merge_chunks(chunks, reranked):
    """
    合并两路检索结果：以 chunks 为底，把 reranked 中尚未出现的片段追加进去。

    用 page_content 做去重，避免同一 chunk 重复占用 context 窗口。
    """
    merged = chunks[:]
    existing = [chunk.page_content for chunk in chunks]
    for chunk in reranked:
        if chunk.page_content not in existing:
            merged.append(chunk)
    return merged


def fetch_context_unranked(question):
    """
    单路向量检索（不做重排）：问题 → embedding → Chroma query → Result 列表。

    n_results=RETRIEVAL_K，先宽后窄（再由 rerank + FINAL_K 截断）。
    """
    query = openai.embeddings.create(model=embedding_model, input=[question]).data[0].embedding
    results = collection.query(query_embeddings=[query], n_results=RETRIEVAL_K)
    chunks = []
    for result in zip(results["documents"][0], results["metadatas"][0]):
        chunks.append(Result(page_content=result[0], metadata=result[1]))
    return chunks


def fetch_context(original_question):
    """
    进阶检索管线：改写 → 双路检索 → 合并 → LLM 重排 → 取 top FINAL_K。

    这是 pro 版相对基础版的核心差异，目标是更高质量的 context 再交给生成模型。
    """
    rewritten_question = rewrite_query(original_question)
    chunks1 = fetch_context_unranked(original_question)
    chunks2 = fetch_context_unranked(rewritten_question)
    chunks = merge_chunks(chunks1, chunks2)
    reranked = rerank(original_question, chunks)
    return reranked[:FINAL_K]


@retry(wait=wait)
def answer_question(question: str, history: list[dict] = []) -> tuple[str, list]:
    """
    Answer a question using RAG and return the answer and the retrieved context

    中文说明：先 fetch_context 得到精排后的 chunks，再拼 messages 调用 LLM；
    返回 (答案文本, 使用的 chunks)，供 UI 或评估展示检索依据。
    """
    chunks = fetch_context(question)
    messages = make_rag_messages(question, history, chunks)
    response = completion(model=MODEL, messages=messages)
    return response.choices[0].message.content, chunks
