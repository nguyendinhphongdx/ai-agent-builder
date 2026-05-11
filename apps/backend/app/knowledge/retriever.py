"""Similarity search across knowledge bases.

Supports two retrieval modes selected per-KB via ``KnowledgeBase.search_mode``:

  ``vector``  pgvector cosine-distance only (the original behaviour).
  ``hybrid``  Reciprocal Rank Fusion of vector + BM25. Better recall
              for keyword-heavy queries that pure embeddings miss
              (proper nouns, code identifiers, exact terms).

RRF score for chunk ``c``::

    score(c) = sum over ranking r ∈ {vector, bm25}:
                 1 / (k + rank_r(c))

with k=60 (the de-facto constant from the original RRF paper).
Chunks that appear in only one ranking still get a score from that
side — RRF is robust to either backend returning nothing.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.knowledge.embedding import build_for_kb
from app.knowledge.reranker import build_for_kb as build_reranker_for_kb
from app.models.document_chunk import DocumentChunk
from app.models.knowledge_base import KnowledgeBase


# Reciprocal Rank Fusion constant. Lower k → top ranks dominate
# harder; 60 is the original Cormack/Clarke/Buettcher value and
# what every public hybrid-search impl ships with.
_RRF_K = 60

# Each leg of the hybrid pull oversamples vs the final top_k so RRF
# has something to fuse — otherwise both legs converge on the same
# rows and fusion adds little value.
_LEG_OVERSAMPLE = 5


@dataclass
class RetrievedChunk:
    content: str
    metadata: dict
    score: float | None = None
    source_document: str | None = None
    chunk_index: int | None = None


class KnowledgeRetriever:
    """Performs similarity search across one or more knowledge bases."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def retrieve(
        self,
        query: str,
        knowledge_base_ids: list[uuid.UUID],
        top_k: int | None = None,
        score_threshold: float | None = None,
    ) -> list[RetrievedChunk]:
        if not knowledge_base_ids:
            return []

        result = await self.db.execute(
            select(KnowledgeBase).where(KnowledgeBase.id.in_(knowledge_base_ids))
        )
        kbs = list(result.scalars().all())
        if not kbs:
            return []

        # Vector searches across embedding-mismatched KBs are nonsense
        # (different vector spaces). BM25 doesn't care — same tsvector
        # dictionary — but we still group by embedding signature so
        # the vector leg stays sane.
        groups: dict[tuple[str, str, int], list[KnowledgeBase]] = {}
        for kb in kbs:
            key = (kb.embedding_provider, kb.embedding_model, kb.embedding_dimensions)
            groups.setdefault(key, []).append(kb)

        first = kbs[0]
        effective_top_k = top_k or first.retrieval_top_k or 5
        effective_threshold = (
            score_threshold if score_threshold is not None else first.retrieval_score_threshold
        )
        # The 0.7 default threshold is calibrated for cosine similarity
        # (0..1). RRF scores live on a different scale (typically
        # 0..0.04 at top_k=5), so applying the same threshold would
        # drop everything. Skip the threshold for hybrid mode and rely
        # on the rank cutoff instead — same trade-off every public
        # hybrid impl makes.
        hybrid_mode = any(getattr(kb, "search_mode", "vector") == "hybrid" for kb in kbs)

        # Reranking: when any KB in the request has a reranker set,
        # we oversample 3× (capped at 50) so the reranker has a real
        # candidate pool, then reduce to top_k via the reranker. Pick
        # the first reranker-enabled KB's config as the deciding one
        # (multi-KB queries with mixed rerank configs are rare).
        rerank_kb = next((k for k in kbs if k.rerank_provider), None)
        if rerank_kb is not None:
            fetch_k = min(max(effective_top_k * 3, rerank_kb.rerank_top_n * 3), 50)
        else:
            fetch_k = effective_top_k

        all_chunks: list[RetrievedChunk] = []
        for group_kbs in groups.values():
            kb_ids = [k.id for k in group_kbs]
            if hybrid_mode:
                chunks = await self._hybrid(query, group_kbs[0], kb_ids, fetch_k)
            else:
                chunks = await self._vector_only(
                    query,
                    group_kbs[0],
                    kb_ids,
                    fetch_k,
                    effective_threshold,
                )
            all_chunks.extend(chunks)

        all_chunks.sort(key=lambda c: c.score or 0, reverse=True)
        candidates = all_chunks[:fetch_k]

        if rerank_kb is not None:
            return await self._rerank(query, candidates, rerank_kb)
        return candidates[:effective_top_k]

    # ── Reranker stage ───────────────────────────────────────────

    async def _rerank(
        self,
        query: str,
        candidates: list[RetrievedChunk],
        rerank_kb: KnowledgeBase,
    ) -> list[RetrievedChunk]:
        """Run the configured reranker against ``candidates`` and
        return them top-down by relevance, capped at ``rerank_top_n``.

        Provider failures degrade gracefully (provider returns the
        identity ranking) — we keep the candidates in their pre-rerank
        order and slice to top_n. Better than 500-ing the retrieval.
        """
        provider = build_reranker_for_kb(rerank_kb)
        top_n = rerank_kb.rerank_top_n or 5
        if provider is None or not candidates:
            return candidates[:top_n]

        results = await provider.arerank(
            query=query,
            documents=[c.content for c in candidates],
            top_n=min(top_n, len(candidates)),
        )
        out: list[RetrievedChunk] = []
        for r in results:
            if 0 <= r.index < len(candidates):
                chunk = candidates[r.index]
                # Replace the score with the reranker's relevance so
                # downstream consumers see a consistent signal.
                out.append(
                    RetrievedChunk(
                        content=chunk.content,
                        metadata=chunk.metadata,
                        score=r.score,
                        source_document=chunk.source_document,
                        chunk_index=chunk.chunk_index,
                    )
                )
        return out

    # ── Vector-only ──────────────────────────────────────────────

    async def _vector_only(
        self,
        query: str,
        sample_kb: KnowledgeBase,
        kb_ids: list[uuid.UUID],
        top_k: int,
        threshold: float | None,
    ) -> list[RetrievedChunk]:
        embeddings = build_for_kb(sample_kb)
        query_embedding = await embeddings.aembed_query(query)
        db_result = await self.db.execute(
            select(
                DocumentChunk.content,
                DocumentChunk.data,
                DocumentChunk.embedding.cosine_distance(query_embedding).label("distance"),
            )
            .where(DocumentChunk.knowledge_base_id.in_(kb_ids))
            .where(DocumentChunk.embedding.isnot(None))
            .order_by("distance")
            .limit(top_k)
        )
        out: list[RetrievedChunk] = []
        for row in db_result.all():
            similarity = 1.0 - (row.distance or 0)
            if threshold is not None and similarity < threshold:
                continue
            metadata = row.data or {}
            out.append(
                RetrievedChunk(
                    content=row.content,
                    metadata=metadata,
                    score=similarity,
                    source_document=metadata.get("source"),
                    chunk_index=metadata.get("chunk_index"),
                )
            )
        return out

    # ── Hybrid (BM25 ∪ vector via RRF) ───────────────────────────

    async def _hybrid(
        self,
        query: str,
        sample_kb: KnowledgeBase,
        kb_ids: list[uuid.UUID],
        top_k: int,
    ) -> list[RetrievedChunk]:
        leg_size = top_k * _LEG_OVERSAMPLE

        # ── Vector leg
        embeddings = build_for_kb(sample_kb)
        query_embedding = await embeddings.aembed_query(query)
        vector_stmt = (
            select(
                DocumentChunk.id,
                DocumentChunk.content,
                DocumentChunk.data,
                DocumentChunk.embedding.cosine_distance(query_embedding).label("distance"),
            )
            .where(DocumentChunk.knowledge_base_id.in_(kb_ids))
            .where(DocumentChunk.embedding.isnot(None))
            .order_by("distance")
            .limit(leg_size)
        )

        # ── BM25 leg via Postgres FTS.
        # ``plainto_tsquery('simple', :q)`` parses unquoted user input
        # safely (no operator injection); ``ts_rank_cd`` is the cover-
        # density ranking — best-in-class for short queries.
        bm25_stmt = text(
            """
            SELECT
              id,
              content,
              metadata AS data,
              ts_rank_cd(content_tsv, plainto_tsquery('simple', :q)) AS rank
            FROM document_chunks
            WHERE knowledge_base_id = ANY(:kb_ids)
              AND content_tsv @@ plainto_tsquery('simple', :q)
            ORDER BY rank DESC
            LIMIT :limit
            """
        )

        vector_rows = (await self.db.execute(vector_stmt)).all()
        bm25_rows = (
            await self.db.execute(
                bm25_stmt,
                {
                    "q": query,
                    "kb_ids": [str(i) for i in kb_ids],
                    "limit": leg_size,
                },
            )
        ).mappings().all()

        # Per-leg rank maps + remember each chunk's row for the final
        # response shape.
        vector_rank: dict[uuid.UUID, int] = {}
        bm25_rank: dict[uuid.UUID, int] = {}
        rows_by_id: dict[uuid.UUID, tuple[str, dict]] = {}

        for i, row in enumerate(vector_rows):
            cid = row.id
            vector_rank[cid] = i + 1
            rows_by_id.setdefault(cid, (row.content, row.data or {}))
        for i, row in enumerate(bm25_rows):
            raw_id = row["id"]
            cid = raw_id if isinstance(raw_id, uuid.UUID) else uuid.UUID(str(raw_id))
            bm25_rank[cid] = i + 1
            rows_by_id.setdefault(cid, (row["content"], row["data"] or {}))

        # Reciprocal Rank Fusion across both legs.
        fused: list[tuple[float, uuid.UUID]] = []
        for cid in rows_by_id:
            score = 0.0
            if cid in vector_rank:
                score += 1.0 / (_RRF_K + vector_rank[cid])
            if cid in bm25_rank:
                score += 1.0 / (_RRF_K + bm25_rank[cid])
            fused.append((score, cid))
        fused.sort(reverse=True)

        out: list[RetrievedChunk] = []
        for score, cid in fused[:top_k]:
            content, metadata = rows_by_id[cid]
            out.append(
                RetrievedChunk(
                    content=content,
                    metadata=metadata,
                    score=score,
                    source_document=metadata.get("source"),
                    chunk_index=metadata.get("chunk_index"),
                )
            )
        return out
