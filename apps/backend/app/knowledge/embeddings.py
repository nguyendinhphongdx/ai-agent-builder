"""Shared embedding model factory for knowledge base operations."""
from __future__ import annotations

from langchain_core.embeddings import Embeddings

from app.config import settings


def build_embeddings(
    provider: str = settings.EMBEDDING_PROVIDER,
    model: str = settings.EMBEDDING_MODEL,
    dimensions: int = settings.EMBEDDING_DIMENSIONS,
    base_url: str | None = settings.OLLAMA_BASE_URL,
) -> Embeddings:
    """Build embedding model from KB config.

    Supports: openai, ollama.
    """
    
    if provider == "ollama":
        from langchain_ollama import OllamaEmbeddings
        return OllamaEmbeddings(
            model=model,
            base_url=base_url or settings.OLLAMA_BASE_URL,
        )

    # openai (default)
    from langchain_openai import OpenAIEmbeddings
    return OpenAIEmbeddings(model=model, dimensions=dimensions)
