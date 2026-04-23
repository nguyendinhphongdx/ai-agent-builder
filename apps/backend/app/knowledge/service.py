import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.agent import AgentKnowledgeBase
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.knowledge_base import KnowledgeBase


async def list_knowledge_bases(db: AsyncSession, user_id: uuid.UUID) -> list[KnowledgeBase]:
    result = await db.execute(
        select(KnowledgeBase)
        .where(KnowledgeBase.user_id == user_id)
        .order_by(KnowledgeBase.updated_at.desc())
    )
    return list(result.scalars().all())


async def get_knowledge_base(
    db: AsyncSession, kb_id: uuid.UUID, user_id: uuid.UUID
) -> KnowledgeBase | None:
    result = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.id == kb_id, KnowledgeBase.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def create_knowledge_base(db: AsyncSession, user_id: uuid.UUID, **kwargs) -> KnowledgeBase:
    # Snapshot embedding config from platform env at create time. Stored on the
    # KB so ingestion + retrieval always agree, even after admin changes defaults.
    kb = KnowledgeBase(
        user_id=user_id,
        embedding_provider=settings.EMBEDDING_PROVIDER,
        embedding_model=settings.EMBEDDING_MODEL,
        embedding_dimensions=settings.EMBEDDING_DIMENSIONS,
        **kwargs,
    )
    db.add(kb)
    await db.flush()
    await db.refresh(kb)
    return kb


async def update_knowledge_base(db: AsyncSession, kb: KnowledgeBase, **kwargs) -> KnowledgeBase:
    for key, value in kwargs.items():
        if value is not None:
            setattr(kb, key, value)
    await db.flush()
    await db.refresh(kb)
    return kb


async def delete_knowledge_base(db: AsyncSession, kb: KnowledgeBase) -> None:
    await db.delete(kb)
    await db.flush()


async def list_documents(db: AsyncSession, kb_id: uuid.UUID) -> list[Document]:
    result = await db.execute(
        select(Document)
        .where(Document.knowledge_base_id == kb_id)
        .order_by(Document.created_at.desc())
    )
    return list(result.scalars().all())


async def get_document(db: AsyncSession, doc_id: uuid.UUID) -> Document | None:
    result = await db.execute(select(Document).where(Document.id == doc_id))
    return result.scalar_one_or_none()


async def list_chunks(
    db: AsyncSession, doc_id: uuid.UUID, limit: int = 50, offset: int = 0
) -> tuple[list[DocumentChunk], int]:
    """Return page of chunks + total count for a document."""
    total = await db.scalar(
        select(func.count(DocumentChunk.id)).where(DocumentChunk.document_id == doc_id)
    ) or 0
    result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == doc_id)
        .order_by(DocumentChunk.chunk_index)
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all()), int(total)


async def count_agents_using_kb(db: AsyncSession, kb_id: uuid.UUID) -> int:
    """Count agents linked to a knowledge base (via agent_knowledge_bases)."""
    total = await db.scalar(
        select(func.count(AgentKnowledgeBase.agent_id)).where(
            AgentKnowledgeBase.knowledge_base_id == kb_id
        )
    )
    return int(total or 0)


async def delete_document(db: AsyncSession, doc: Document) -> None:
    # Update KB counters
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == doc.knowledge_base_id)
    )
    kb = result.scalar_one_or_none()
    if kb:
        kb.total_documents = max(0, (kb.total_documents or 0) - 1)
        kb.total_chunks = max(0, (kb.total_chunks or 0) - (doc.chunk_count or 0))

    await db.delete(doc)
    await db.flush()
