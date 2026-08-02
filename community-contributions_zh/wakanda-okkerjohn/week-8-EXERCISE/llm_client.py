# 中文注释版：下方为便于小白阅读的中文旁注；逻辑与标识符未改。
"""
OpenRouter LLM 客户端 – API 基本 URL 和密钥的单一位置。

OpenRouter LLM client – single place for API base URL and key.
"""
from openai import OpenAI

from config import OPENROUTER_BASE_URL, OPENROUTER_API_KEY, OPENROUTER_MODEL


def get_client() -> OpenAI:
    """Return an OpenAI-compatible client configured for OpenRouter."""
    return OpenAI(base_url=OPENROUTER_BASE_URL, api_key=OPENROUTER_API_KEY)


def get_model() -> str:
    """Return the OpenRouter model id to use (e.g. openai/gpt-4o-mini)."""
    return OPENROUTER_MODEL
