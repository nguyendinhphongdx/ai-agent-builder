"""Unified LLM provider factory - tạo LLM instance từ model_id + config.

Model ID format: "provider/model-name" — VD "openai/gpt-4o", "anthropic/claude-sonnet-4-20250514".
Hỗ trợ: OpenAI, Anthropic, Google, Ollama.
"""

from __future__ import annotations

from typing import Any

from langchain_core.language_models import BaseChatModel


def split_model_id(model_id: str) -> tuple[str, str]:
    """Parse "provider/model" thành (provider, model_name).

    Split tại dấu '/' đầu tiên để cho phép model name chứa '/' (VD "huggingface/meta-llama/Llama-3").
    """
    if "/" not in model_id:
        raise ValueError(
            f"Invalid model_id '{model_id}'. Expected format 'provider/model', e.g. 'openai/gpt-4o'"
        )
    provider, name = model_id.split("/", 1)
    return provider, name


def build_llm(
    model_id: str,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    base_url: str | None = None,
    api_key: str | None = None,
    **kwargs: Any,
) -> BaseChatModel:
    """Tạo LLM instance từ model_id (format "provider/model").

    Args:
        model_id: "openai/gpt-4o", "anthropic/claude-sonnet-4-20250514", ...
        temperature: độ sáng tạo
        max_tokens: số token tối đa cho response
        base_url: URL tùy chỉnh (dùng cho Ollama hoặc API proxy)
        api_key: API key ghi đè (nếu None, dùng biến môi trường)
        **kwargs: tham số bổ sung truyền thẳng cho LLM constructor
    """
    provider, model = split_model_id(model_id)
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

    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        extra = {}
        if base_url:
            extra["base_url"] = base_url
        return ChatOpenAI(model=model, **common, **extra)

    elif provider == "azure":
        # Azure OpenAI — three pieces required:
        #   azure_endpoint  https://<resource>.openai.azure.com
        #   api_version     e.g. "2024-08-01-preview"
        #   azure_deployment  the Azure-side deployment name; model_id
        #                     suffix is treated as the deployment id.
        # Endpoint + version come from the credential's ``base_url``
        # field (we overload it as JSON-ish "endpoint|version" to
        # avoid a credentials schema migration). Senders may also
        # pass them explicitly via kwargs.
        from langchain_openai import AzureChatOpenAI

        azure_endpoint = kwargs.pop("azure_endpoint", None) or base_url
        api_version = kwargs.pop("api_version", "2024-08-01-preview")
        if not azure_endpoint:
            raise ValueError(
                "Azure provider requires base_url (endpoint URL) or "
                "azure_endpoint kwarg"
            )
        # AzureChatOpenAI doesn't accept the plain ``base_url`` kw —
        # strip from common, re-thread as azure_endpoint.
        return AzureChatOpenAI(
            azure_deployment=model,
            azure_endpoint=azure_endpoint,
            api_version=api_version,
            **common,
        )

    elif provider == "bedrock":
        # AWS Bedrock — credentials resolve via boto3's standard
        # chain (env, ~/.aws/credentials, IAM role). The credential
        # row carries optional ``aws_access_key_id`` +
        # ``aws_secret_access_key`` we map to kwargs here.
        from langchain_aws import ChatBedrock

        region = kwargs.pop("region_name", None) or "us-east-1"
        # ChatBedrock uses ``model_id`` (their term) and doesn't
        # accept ``api_key`` — strip from common.
        common.pop("api_key", None)
        return ChatBedrock(
            model_id=model,
            region_name=region,
            **common,
        )

    else:
        raise ValueError(f"Unsupported provider: {provider}")


def build_llm_from_agent(agent, api_key: str | None = None) -> BaseChatModel:
    """Tạo LLM từ cấu hình Agent model (tiện dùng trong executor)."""
    config = agent.llm_config or {}
    return build_llm(
        model_id=agent.model_id,
        temperature=config.get("temperature", 0.7),
        max_tokens=config.get("max_tokens", 4096),
        base_url=config.get("base_url"),
        api_key=api_key,
    )
