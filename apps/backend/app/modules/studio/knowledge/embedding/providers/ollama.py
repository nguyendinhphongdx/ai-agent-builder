"""Ollama embedding provider — local, no API key required."""
from __future__ import annotations

import os

from langchain_core.embeddings import Embeddings
from langchain_ollama import OllamaEmbeddings

from ..registry import register


def _build(model: str, dim: int) -> Embeddings:
    # Ollama model name implies its dimension — `dim` is ignored at construction.
    # If admin misconfigures (e.g. EMBEDDING_MODEL=nomic-embed-text with
    # EMBEDDING_DIMENSIONS=1024), the mismatch surfaces when pgvector rejects
    # the inserted vector on the first ingest.
    del dim
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    return OllamaEmbeddings(model=model, base_url=base_url)


register("ollama", _build)
