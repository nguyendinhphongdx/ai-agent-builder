import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AgentKnowledgeBase
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.knowledge_base import KnowledgeBase
from app.platform.config import settings
from app.platform.context import current_user_id, current_workspace_id_or_none


def _scope_filter(stmt):
    """Restrict to KBs in the current workspace."""
    workspace_id = current_workspace_id_or_none()
    if workspace_id is None:
        return stmt
    return stmt.where(KnowledgeBase.workspace_id == workspace_id)


async def list_knowledge_bases(db: AsyncSession) -> list[KnowledgeBase]:
    stmt = (
        select(KnowledgeBase)
        .where(KnowledgeBase.user_id == current_user_id())
        .order_by(KnowledgeBase.updated_at.desc())
    )
    result = await db.execute(_scope_filter(stmt))
    return list(result.scalars().all())


async def get_knowledge_base(
    db: AsyncSession, kb_id: uuid.UUID
) -> KnowledgeBase | None:
    stmt = select(KnowledgeBase).where(
        KnowledgeBase.id == kb_id,
        KnowledgeBase.user_id == current_user_id(),
    )
    result = await db.execute(_scope_filter(stmt))
    return result.scalar_one_or_none()


async def get_knowledge_base_unscoped(
    db: AsyncSession, kb_id: uuid.UUID
) -> KnowledgeBase | None:
    """Fetch KB without user/workspace check. Used by trusted
    background tasks only (workflow runner, ingestion worker)."""
    result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    return result.scalar_one_or_none()


async def create_knowledge_base(db: AsyncSession, **kwargs) -> KnowledgeBase:
    # Snapshot embedding config from platform env at create time. Stored on the
    # KB so ingestion + retrieval always agree, even after admin changes defaults.
    kwargs.setdefault("workspace_id", current_workspace_id_or_none())
    kb = KnowledgeBase(
        user_id=current_user_id(),
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


async def reset_document_for_reprocess(db: AsyncSession, doc: Document) -> Document:
    """Clear existing chunks + reset doc status so ingestion can run again.

    Used by the `/reprocess` endpoint to retry a failed or stale document
    without forcing the user to re-upload. Embedding config still comes from
    the parent KB at run time, so re-processing picks up any KB settings
    changes.
    """
    from sqlalchemy import delete as sql_delete

    # Wipe prior chunks so we don't double up
    await db.execute(
        sql_delete(DocumentChunk).where(DocumentChunk.document_id == doc.id)
    )

    # Roll back KB counters for this doc's previous chunks
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == doc.knowledge_base_id)
    )
    kb = result.scalar_one_or_none()
    if kb:
        kb.total_chunks = max(0, (kb.total_chunks or 0) - (doc.chunk_count or 0))
        # total_documents stays — we're reusing the same doc row

    # Reset fields for a fresh run
    doc.status = "pending"
    doc.processing_phase = "queued"
    doc.processing_progress = 0
    doc.chunk_count = 0
    doc.token_count = None
    doc.error_message = None
    doc.processing_started_at = None
    doc.processing_completed_at = None

    await db.flush()
    await db.refresh(doc)
    return doc


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
