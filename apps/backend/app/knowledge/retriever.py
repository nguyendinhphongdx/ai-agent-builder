"""Vector similarity search across knowledge bases using pgvector."""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.knowledge.embedding import build_for_kb
from app.models.document_chunk import DocumentChunk
from app.models.knowledge_base import KnowledgeBase


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

        # Group KBs by embedding signature — querying across mismatched models
        # produces meaningless distances (different vector spaces / dimensions).
        groups: dict[tuple[str, str, int], list[KnowledgeBase]] = {}
        for kb in kbs:
            key = (kb.embedding_provider, kb.embedding_model, kb.embedding_dimensions)
            groups.setdefault(key, []).append(kb)

        # Take top_k / threshold from the first KB if caller didn't override.
        first = kbs[0]
        effective_top_k = top_k or first.retrieval_top_k or 5
        effective_threshold = (
            score_threshold if score_threshold is not None else first.retrieval_score_threshold
        )

        all_chunks: list[RetrievedChunk] = []
        for group_kbs in groups.values():
            embeddings = build_for_kb(group_kbs[0])
            query_embedding = await embeddings.aembed_query(query)

            db_result = await self.db.execute(
                select(
                    DocumentChunk.content,
                    DocumentChunk.data,
                    DocumentChunk.embedding.cosine_distance(query_embedding).label("distance"),
                )
                .where(DocumentChunk.knowledge_base_id.in_([k.id for k in group_kbs]))
                .where(DocumentChunk.embedding.isnot(None))
                .order_by("distance")
                .limit(effective_top_k)
            )

            for row in db_result.all():
                similarity = 1.0 - (row.distance or 0)
                if effective_threshold is not None and similarity < effective_threshold:
                    continue
                metadata = row.data or {}
                all_chunks.append(
                    RetrievedChunk(
                        content=row.content,
                        metadata=metadata,
                        score=similarity,
                        source_document=metadata.get("source"),
                        chunk_index=metadata.get("chunk_index"),
                    )
                )

        all_chunks.sort(key=lambda c: c.score or 0, reverse=True)
        return all_chunks[:effective_top_k]
