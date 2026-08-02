import ast
from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage, convert_to_messages
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

load_dotenv(override=True)

MODEL = "gpt-4.1-nano"
DB_NAME = str(Path(__file__).parent.parent / "vector_db")

embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
RETRIEVAL_K = 10

SYSTEM_PROMPT = """
You are a east logistics assistant. Use ONLY the data provided below to answer the question.
If the answer cannot be determined from the data, say "No confident match in data."

DATA:
{context}

QUESTION:
{question}

INSTRUCTIONS:
- Answer concisely.
- Do not invent facts.
"""

vectorstore = Chroma(persist_directory=DB_NAME, embedding_function=embeddings)
retriever = vectorstore.as_retriever()
llm = ChatOpenAI(temperature=0, model_name=MODEL)


def fetch_context(question: str, top_k: int = RETRIEVAL_K):
    """查询 Chroma 矢量存储并返回 top_k Document 对象。"""

    results = vectorstore.similarity_search_with_relevance_scores(question, k=top_k)

    if not results:
        return []

    documents = []

    for doc, score in results:
        doc.metadata["relevance_score"] = float(score)
        documents.append(doc)

    return documents


def fetch_filters(question: str) -> dict:
    """获取问题的过滤器。"""
    prompt = f"""
    You are a helpful assistant that extracts filters from a question.
    Given a question, extract the sensible filters that can be used to filter the data.
    
    example is:
    quest = "Find shipments from Nairobi to Mombasa delivered last week under 50kg"
    filters = {{"origin": "Nairobi", "dest": "Mombasa", "status": "delivered", "weight": {{"$lt": 50}} }}

    Only return the dictionary of filters, no other text.
    The question is: {question}
    """
    messages = [{"role": "system", "content": prompt}]
    response = llm.invoke(messages)
    return ast.literal_eval(response.content)  # ty:ignore[invalid-argument-type]


def answer_question(
    question: str, history: list[dict] = []
) -> tuple[str, list[Document]]:
    """
    Answer the given question with RAG; return the answer and the context documents.
    """
    # 过滤器= fetch_filters（问题）
    context = fetch_context(question)
    prompt_context = "\n\n".join(doc.page_content for doc in context)
    system_prompt = SYSTEM_PROMPT.format(question=question, context=prompt_context)
    messages = [SystemMessage(content=system_prompt)]
    messages.extend(convert_to_messages(history))
    messages.append(HumanMessage(content=question))
    response = llm.invoke(messages)
    return response.content, context
