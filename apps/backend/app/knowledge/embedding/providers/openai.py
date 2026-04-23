"""OpenAI embedding provider — requires OPENAI_EMBEDDING_API_KEY."""
from __future__ import annotations

import os

from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings

from ..registry import register


def _build(model: str, dim: int) -> Embeddings:
    api_key = os.environ.get("OPENAI_EMBEDDING_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_EMBEDDING_API_KEY is required for OpenAI embeddings"
        )
    return OpenAIEmbeddings(model=model, dimensions=dim, api_key=api_key)


register("openai", _build)
