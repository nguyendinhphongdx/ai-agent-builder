"""Unified LLM provider factory - tạo LLM instance từ provider name + config.

Hỗ trợ: OpenAI, Anthropic, Ollama (local).
Tập trung logic tạo LLM ở một chỗ thay vì rải rác trong executor, workflow nodes, ...
"""

from __future__ import annotations

from typing import Any

from langchain_core.language_models import BaseChatModel


# Danh sách model mặc định cho mỗi provider
DEFAULT_MODELS = {
    "openai": "gpt-4o",
    "anthropic": "claude-sonnet-4-20250514",
    "ollama": "llama3.1",
}

# Danh sách model khả dụng cho frontend hiển thị
AVAILABLE_MODELS = {
    "openai": [
        {"id": "gpt-4o", "name": "GPT-4o", "context_window": 128000},
        {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "context_window": 128000},
        {"id": "gpt-4-turbo", "name": "GPT-4 Turbo", "context_window": 128000},
        {"id": "o3-mini", "name": "o3-mini", "context_window": 200000},
    ],
    "anthropic": [
        {"id": "claude-sonnet-4-20250514", "name": "Claude Sonnet 4", "context_window": 200000},
        {"id": "claude-opus-4-20250514", "name": "Claude Opus 4", "context_window": 200000},
        {"id": "claude-haiku-4-20250414", "name": "Claude Haiku 4", "context_window": 200000},
    ],
    "ollama": [
        {"id": "llama3.1", "name": "Llama 3.1", "context_window": 128000},
        {"id": "mistral", "name": "Mistral", "context_window": 32000},
        {"id": "codellama", "name": "Code Llama", "context_window": 16000},
        {"id": "gemma2", "name": "Gemma 2", "context_window": 8192},
    ],
}


def build_llm(
    provider: str = "openai",
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    base_url: str | None = None,
    api_key: str | None = None,
    **kwargs: Any,
) -> BaseChatModel:
    """Tạo LLM instance dựa trên provider.

    Args:
        provider: "openai", "anthropic", "google", hoặc "ollama"
        model: tên model (nếu None, dùng model mặc định của provider)
        temperature: độ sáng tạo (0.0 - 1.0)
        max_tokens: số token tối đa cho response
        base_url: URL tùy chỉnh (dùng cho Ollama hoặc API proxy)
        api_key: API key ghi đè (nếu None, dùng biến môi trường)
        **kwargs: tham số bổ sung truyền thẳng cho LLM constructor
    """
    model = model or DEFAULT_MODELS.get(provider, "gpt-4o")
    common = {"temperature": temperature, "max_tokens": max_tokens, **kwargs}
    if api_key:
        common["api_key"] = api_key

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model, **common)

    elif provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=model, **common)

    elif provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=model,
            base_url=base_url or "http://localhost:11434",
            temperature=temperature,
            num_predict=max_tokens,
        )

    else:  # openai (default)
        from langchain_openai import ChatOpenAI
        extra = {}
        if base_url:
            extra["base_url"] = base_url
        return ChatOpenAI(model=model, **common, **extra)


def build_llm_from_agent(agent, api_key: str | None = None) -> BaseChatModel:
    """Tạo LLM từ cấu hình Agent model (tiện dùng trong executor)."""
    config = agent.llm_config or {}
    return build_llm(
        provider=agent.llm_provider,
        model=agent.llm_model,
        temperature=config.get("temperature", 0.7),
        max_tokens=config.get("max_tokens", 4096),
        base_url=config.get("base_url"),
        api_key=api_key,
    )
