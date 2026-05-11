"""Cohere reranker — managed API.

Endpoint: POST https://api.cohere.com/v2/rerank
Request:  {model, query, documents: [str, ...], top_n}
Response: {results: [{index: int, relevance_score: float}, ...]}

API key read from ``settings.COHERE_API_KEY``. Per-KB API keys can
land later via the ai_credentials machinery; for v1 the platform
single key is the simpler call.
"""
from __future__ import annotations

import logging

import httpx

from app.config import settings
from app.knowledge.reranker.base import RerankerProvider, RerankResult

logger = logging.getLogger("agentforge")

_DEFAULT_MODEL = "rerank-3.5"  # Cohere's current English/multilingual default.
_API_BASE = "https://api.cohere.com/v2/rerank"
_TIMEOUT_SECONDS = 8.0


class CohereReranker(RerankerProvider):
    def __init__(self, *, model: str = _DEFAULT_MODEL) -> None:
        self._model = model

    async def arerank(
        self,
        *,
        query: str,
        documents: list[str],
        top_n: int,
    ) -> list[RerankResult]:
        if not documents:
            return []
        top_n = min(top_n, len(documents))

        api_key = (settings.COHERE_API_KEY or "").strip()
        if not api_key:
            logger.warning(
                "cohere reranker: COHERE_API_KEY not set — falling back to input order"
            )
            return [RerankResult(index=i, score=0.0) for i in range(top_n)]

        payload = {
            "model": self._model,
            "query": query,
            "documents": documents,
            "top_n": top_n,
        }
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
                resp = await client.post(
                    _API_BASE,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                )
            if resp.status_code >= 400:
                logger.warning(
                    "cohere reranker: %d %s — falling back to input order",
                    resp.status_code,
                    resp.text[:200],
                )
                return [RerankResult(index=i, score=0.0) for i in range(top_n)]
            body = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("cohere reranker: %s — falling back to input order", exc)
            return [RerankResult(index=i, score=0.0) for i in range(top_n)]

        results = body.get("results") or []
        # Trust the API's ordering (most relevant first) but pin the
        # types since we expose them downstream.
        return [
            RerankResult(
                index=int(r.get("index", 0)),
                score=float(r.get("relevance_score", 0.0)),
            )
            for r in results
        ]
