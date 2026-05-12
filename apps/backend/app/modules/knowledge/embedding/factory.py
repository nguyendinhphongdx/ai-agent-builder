"""High-level factory used by ingestion + retrieval."""
from __future__ import annotations

from langchain_core.embeddings import Embeddings

from app.models.knowledge_base import KnowledgeBase
from app.platform.config import settings

from .registry import build


def build_default() -> Embeddings:
    """Build embeddings using current platform config (settings.EMBEDDING_*)."""
    return build(
        settings.EMBEDDING_PROVIDER,
        settings.EMBEDDING_MODEL,
        settings.EMBEDDING_DIMENSIONS,
    )


def build_for_kb(kb: KnowledgeBase) -> Embeddings:
    """Build embeddings using KB's snapshotted provider/model/dim.

    Ingestion and retrieval MUST use this (not `build_default`) so vectors
    are created and queried with matching dimensions even after admin
    changes the platform defaults.
    """
    return build(kb.embedding_provider, kb.embedding_model, kb.embedding_dimensions)
