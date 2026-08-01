"""
Week 5 进阶版（pro）知识入库（ingest）：LLM 智能分块 + 写入预处理向量库。

什么是 ingest（入库）？
  RAG 上线前的「离线准备」：把公司知识库文档切成块 → 算向量（embeddings）→ 存进向量数据库。
  用户提问时再「在线检索」这些块。分块质量直接影响检索能不能找对。

与基础版 implementation/ingest.py 的差异：
  - 不用固定字符窗口切分，而是让 LLM 按语义切成 Chunk（含 headline、summary、原文）
  - 入库文本 = headline + summary + original_text，检索时更容易「命中」用户问法
    （用户很少逐字引用合同原文，更常问「退款政策是什么」——headline/summary 更像问法）
  - 使用 Chroma PersistentClient 写入 preprocessed_db（供 pro answer 使用）
  - 可用多进程 Pool 并行处理文档（注意 API 限流时把 WORKERS 调为 1）

RAG（Retrieval-Augmented Generation）离线阶段：
  加载 Markdown → LLM chunking → embeddings → vector DB（preprocessed_db）
"""

from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from chromadb import PersistentClient
from tqdm import tqdm
from litellm import completion
from multiprocessing import Pool
from tenacity import retry, wait_exponential


load_dotenv(override=True)

MODEL = "openai/gpt-4.1-nano"

DB_NAME = str(Path(__file__).parent.parent / "preprocessed_db")
collection_name = "docs"
embedding_model = "text-embedding-3-large"
KNOWLEDGE_BASE_PATH = Path(__file__).parent.parent / "knowledge-base"
# 用文档长度估算「大概需要多少块」，写入 prompt 给 LLM 作参考（不是硬性切割长度）
AVERAGE_CHUNK_SIZE = 100
# tenacity 指数退避：失败后等待时间在 min~max 秒之间指数增长，减轻 API 限流抖动
wait = wait_exponential(multiplier=1, min=10, max=240)


# 并行进程数：越大越快，也越容易触发 rate limit；遇 429 请改为 1
WORKERS = 3

openai = OpenAI()


class Result(BaseModel):
    """写入向量库前的统一结果形态：正文 + metadata（来源路径、文档类型等）。"""

    page_content: str
    metadata: dict


class Chunk(BaseModel):
    """
    LLM 产出的单个语义块：标题 + 摘要 + 原文。

    headline / summary 用「更像用户问题」的表述增强检索命中率；
    original_text 保持原文不变，回答时仍有准确细节可依。

    Field(description=...) 的英文会进入 Structured Outputs schema，告诉模型每个字段该写什么——勿改字面量。
    """

    headline: str = Field(
        description="A brief heading for this chunk, typically a few words, that is most likely to be surfaced in a query",
    )
    summary: str = Field(
        description="A few sentences summarizing the content of this chunk to answer common questions"
    )
    original_text: str = Field(
        description="The original text of this chunk from the provided document, exactly as is, not changed in any way"
    )

    def as_result(self, document):
        """
        把 Chunk 拼成 Result：检索用的 page_content = 标题+摘要+原文。

        嵌入向量是对整段 page_content 计算的，所以「问法友好」的 headline/summary
        会进入向量空间，提高语义检索召回。
        """
        metadata = {"source": document["source"], "type": document["type"]}
        return Result(
            page_content=self.headline + "\n\n" + self.summary + "\n\n" + self.original_text,
            metadata=metadata,
        )


class Chunks(BaseModel):
    """LLM 结构化输出：一篇文档对应的多个 Chunk（外层包装列表）。"""

    chunks: list[Chunk]


def fetch_documents():
    """
    A homemade version of the LangChain DirectoryLoader

    中文说明：遍历 knowledge-base 各类型子目录，读取全部 .md，
    返回 {"type", "source", "text"} 字典列表（不依赖 LangChain loader）。
    type 通常是文件夹名（如 contracts、employees），之后会写进 Chroma metadata。
    """

    documents = []

    for folder in KNOWLEDGE_BASE_PATH.iterdir():
        doc_type = folder.name
        for file in folder.rglob("*.md"):
            with open(file, "r", encoding="utf-8") as f:
                documents.append({"type": doc_type, "source": file.as_posix(), "text": f.read()})

    print(f"Loaded {len(documents)} documents")
    return documents


def make_prompt(document):
    """
    构造「请把文档切成重叠 chunks」的 LLM 提示词。

    how_many 根据文档长度与 AVERAGE_CHUNK_SIZE 粗估块数，引导模型不要切太少；
    要求块之间约 25% / ~50 词重叠，提升 retrieval 时边界信息的命中率。

    为什么要 overlap（重叠）？
      固定/语义切分都可能把「一问一答」劈成两半；重叠让关键句同时出现在相邻块里，
      检索时不容易「刚好漏掉半句」。
    """
    how_many = (len(document["text"]) // AVERAGE_CHUNK_SIZE) + 1
    return f"""
You take a document and you split the document into overlapping chunks for a KnowledgeBase.

The document is from the shared drive of a company called Insurellm.
The document is of type: {document["type"]}
The document has been retrieved from: {document["source"]}

A chatbot will use these chunks to answer questions about the company.
You should divide up the document as you see fit, being sure that the entire document is returned across the chunks - don't leave anything out.
This document should probably be split into at least {how_many} chunks, but you can have more or less as appropriate, ensuring that there are individual chunks to answer specific questions.
There should be overlap between the chunks as appropriate; typically about 25% overlap or about 50 words, so you have the same text in multiple chunks for best retrieval results.

For each chunk, you should provide a headline, a summary, and the original text of the chunk.
Together your chunks should represent the entire document with overlap.

Here is the document:

{document["text"]}

Respond with the chunks.
"""


def make_messages(document):
    """把 make_prompt 包成 litellm / chat API 所需的 messages 列表。"""
    return [
        {"role": "user", "content": make_prompt(document)},
    ]


@retry(wait=wait)
def process_document(document):
    """
    对单篇文档调用 LLM，得到结构化 Chunks，再转成 Result 列表。

    @retry：遇瞬时 API 错误时按指数退避重试，适合批量 ingest。
    response_format=Chunks：强制模型返回符合 Pydantic schema 的 JSON，便于可靠解析。
    """
    messages = make_messages(document)
    response = completion(model=MODEL, messages=messages, response_format=Chunks)
    reply = response.choices[0].message.content
    doc_as_chunks = Chunks.model_validate_json(reply).chunks
    return [chunk.as_result(document) for chunk in doc_as_chunks]


def create_chunks(documents):
    """
    Create chunks using a number of workers in parallel.
    If you get a rate limit error, set the WORKERS to 1.

    中文说明：用 multiprocessing.Pool 并行 process_document；
    imap_unordered + tqdm 显示进度（完成顺序可能乱，但我们只 extend 结果，不依赖顺序）。
    限流时务必将 WORKERS 设为 1。
    """
    chunks = []
    with Pool(processes=WORKERS) as pool:
        for result in tqdm(pool.imap_unordered(process_document, documents), total=len(documents)):
            chunks.extend(result)
    return chunks


def create_embeddings(chunks):
    """
    批量计算 embeddings 并写入 Chroma collection。

    embedding（嵌入）：把文本变成高维向量，语义相近的文本在向量空间里距离更近。
    之后用户问题也会被嵌入，再用「近邻搜索」找出相关文档块——这就是向量检索。

    若同名 collection 已存在则删除后重建（保证本次 ingest 是干净全量重建）；
    ids / documents / metadatas / embeddings 一一对应。
    完成后打印 collection.count() 确认入库条数。
    """
    chroma = PersistentClient(path=DB_NAME)
    if collection_name in [c.name for c in chroma.list_collections()]:
        chroma.delete_collection(collection_name)

    texts = [chunk.page_content for chunk in chunks]
    emb = openai.embeddings.create(model=embedding_model, input=texts).data
    vectors = [e.embedding for e in emb]

    collection = chroma.get_or_create_collection(collection_name)

    ids = [str(i) for i in range(len(chunks))]
    metas = [chunk.metadata for chunk in chunks]

    collection.add(ids=ids, embeddings=vectors, documents=texts, metadatas=metas)
    print(f"Vectorstore created with {collection.count()} documents")


if __name__ == "__main__":
    # 完整 pro ingest：加载 → LLM 分块 → 嵌入写入 preprocessed_db
    documents = fetch_documents()
    chunks = create_chunks(documents)
    create_embeddings(chunks)
    print("Ingestion complete")
