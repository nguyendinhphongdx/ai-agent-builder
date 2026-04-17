"""Vector similarity search across knowledge bases using pgvector."""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.knowledge.embeddings import build_embeddings
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

        # Load KB configs to get embedding settings and retrieval params
        result = await self.db.execute(
            select(KnowledgeBase).where(KnowledgeBase.id.in_(knowledge_base_ids))
        )
        kbs = result.scalars().all()
        if not kbs:
            return []

        # Use first KB's config for embedding
        kb = kbs[0]
        effective_top_k = top_k or kb.retrieval_top_k or 5
        effective_threshold = score_threshold if score_threshold is not None else kb.retrieval_score_threshold

        # Build embeddings from KB config
        embeddings = build_embeddings(
            provider=kb.embedding_provider,
            model=kb.embedding_model,
            dimensions=kb.embedding_dimensions,
        )

        # Embed the query
        query_embedding = await embeddings.aembed_query(query)

        # pgvector cosine distance search
        db_result = await self.db.execute(
            select(
                DocumentChunk.content,
                DocumentChunk.data,
                DocumentChunk.embedding.cosine_distance(query_embedding).label("distance"),
            )
            .where(DocumentChunk.knowledge_base_id.in_(knowledge_base_ids))
            .where(DocumentChunk.embedding.isnot(None))
            .order_by("distance")
            .limit(effective_top_k)
        )

        chunks = []
        for row in db_result.all():
            similarity = 1.0 - (row.distance or 0)

            # Filter by score threshold
            if effective_threshold is not None and similarity < effective_threshold:
                continue

            metadata = row.data or {}
            chunks.append(
                RetrievedChunk(
                    content=row.content,
                    metadata=metadata,
                    score=similarity,
                    source_document=metadata.get("source"),
                    chunk_index=metadata.get("chunk_index"),
                )
            )

        return chunks
