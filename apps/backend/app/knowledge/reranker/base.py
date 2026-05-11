"""Reranker provider interface.

Implementations:
  CohereReranker  managed API (HTTP).
  BGEReranker     self-hosted via HF Inference Endpoint (future).
  VoyageReranker  managed (future).

The contract is intentionally narrow — a single ``arerank`` call.
Providers are responsible for HTTP / batching / retries internally;
the retriever just sees a list of ``(index, relevance_score)``
pointing back into the input docs.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class RerankResult:
    """One reranked entry. ``index`` is the position in the original
    candidate list (so the retriever can join back to the chunk row)
    and ``score`` is whatever the provider returned, on whatever
    scale they use — typically 0..1 but consult provider docs."""

    index: int
    score: float


class RerankerProvider(ABC):
    """Score a candidate list against a query and return them ranked
    most-relevant-first.

    Implementations should:
      - Tolerate empty ``documents`` (return []).
      - Cap top_n at len(documents).
      - Never raise on transient API failures — log + return the
        original order (rank by input position). Retrieval should
        degrade gracefully when the reranker is unhealthy.
    """

    @abstractmethod
    async def arerank(
        self,
        *,
        query: str,
        documents: list[str],
        top_n: int,
    ) -> list[RerankResult]:
        ...
