from openai import OpenAI
from config import OLLAMA_BASE_URL, MODEL_NAME


def create_client() -> OpenAI:
    """创建并返回指向 Ollama 的 OpenAI 兼容客户端。

    返回：
        OpenAI：配置的客户端实例。"""
    return OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")


def get_response(messages: list, client: OpenAI) -> str:
    """将当前对话历史记录发送给 LLM 并返回其响应。

    参数：
        消息（列表）：到目前为止的完整对话历史记录。
        客户端 (OpenAI)：OpenAI 客户端实例。

    返回：
        str：LLM 的回复文本。"""
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages
    )
    return response.choices[0].message.content
