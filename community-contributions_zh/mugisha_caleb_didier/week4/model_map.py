"""中文注释版：逻辑与标识符保持原文，便于 import 与运行。"""
# 将课程中找到的无前缀模型名称映射到其确切的 OpenRouter ID。
# 由转换器的 SYSTEM_PROMPT 使用，以便 LLM 获得确定性模型名称映射
# 而不是依赖模糊的通配符前缀规则。

MODEL_MAP = {
    # 开放人工智能
    "gpt-4o": "openai/gpt-4o",
    "gpt-4o-mini": "openai/gpt-4o-mini",
    "gpt-4.1": "openai/gpt-4.1",
    "gpt-4.1-mini": "openai/gpt-4.1-mini",
    "gpt-4.1-nano": "openai/gpt-4.1-nano",
    "gpt-5": "openai/gpt-5",
    "gpt-5-mini": "openai/gpt-5-mini",
    "gpt-5-nano": "openai/gpt-5-nano",
    "gpt-5.1": "openai/gpt-5.1",
    "gpt-5.2": "openai/gpt-5.2",
    # 人择
    "claude-sonnet-4-5-20250929": "anthropic/claude-sonnet-4-5-20250929",
    "claude-sonnet-4.5": "anthropic/claude-sonnet-4.5",
    "claude-sonnet-4.6": "anthropic/claude-sonnet-4.6",
    "claude-opus-4.5": "anthropic/claude-opus-4.5",
    "claude-opus-4.6": "anthropic/claude-opus-4.6",
    "claude-haiku-4-5": "anthropic/claude-haiku-4-5",
    "claude-3.5-haiku": "anthropic/claude-3.5-haiku",
    # 谷歌
    "gemini-2.0-flash": "google/gemini-2.0-flash",
    "gemini-2.5-flash-lite": "google/gemini-2.5-flash-lite",
    "gemini-2.5-pro": "google/gemini-2.5-pro",
    "gemini-3-flash-preview": "google/gemini-3-flash-preview",
    "gemini-3-pro-preview": "google/gemini-3-pro-preview",
    # 人工智能
    "grok-2": "x-ai/grok-2",
    "grok-4": "x-ai/grok-4",
    # 深度搜索
    "deepseek-coder-v2": "deepseek/deepseek-coder-v2",
    "deepseek-chat": "deepseek/deepseek-chat",
}
