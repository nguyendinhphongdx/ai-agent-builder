"""Reranker dispatch — pick the right provider for a KB.

Mirrors the embedding-provider pattern: a tiny factory keyed on the
KB's ``rerank_provider`` field. Returns ``None`` when no reranker
is configured so the retriever can short-circuit.
"""
from __future__ import annotations

from app.models.knowledge_base import KnowledgeBase
from app.modules.studio.knowledge.reranker.base import RerankerProvider
from app.modules.studio.knowledge.reranker.providers.cohere import CohereReranker


def build_for_kb(kb: KnowledgeBase) -> RerankerProvider | None:
    """Resolve the configured reranker, or ``None`` to skip."""
    provider = (kb.rerank_provider or "").lower().strip() or None
    if provider is None:
        return None
    if provider == "cohere":
        return CohereReranker(model=kb.rerank_model or "rerank-3.5")
    # Unknown provider → log + skip rather than raise: retrieval
    # should never hard-fail on bad config.
    import logging

    logging.getLogger("agentforge").warning(
        "reranker: KB %s configured with unknown provider %r — skipping",
        kb.id,
        provider,
    )
    return None
