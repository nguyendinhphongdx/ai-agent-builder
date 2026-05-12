"""Document ingestion pipeline: parse -> chunk -> embed -> store in pgvector.

Pipeline phases (also emitted via socket to `user:{id}` so frontend can show progress):
  queued -> parsing -> chunking -> embedding -> ready / failed

Parsing is delegated to :mod:`app.platform.extractors` so every consumer of uploaded
files (KB ingestion, chat attachments, …) shares the same format support.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.knowledge_base import KnowledgeBase
from app.platform.extractors import (
    ExtractionError,
    Extractor,
    UnsupportedFormatError,
)
from app.platform.storage import get_storage

logger = logging.getLogger("agentforge")


EMBED_BATCH_SIZE = 32


async def parse_document(file_path: str, file_type: str) -> str:
    """Parse an uploaded document to raw text.

    ``file_path`` here is a storage key (``"kb/{id}/{hash}.pdf"``) — we resolve
    it to a URL through the storage backend so parsing works uniformly on
    local disk, S3, GCS or anything else behind the :class:`StorageBackend`
    interface.

    Raises ``ValueError`` with a user-friendly message on failure.
    """
    url = get_storage().get_url(file_path, access="private")
    try:
        result = await Extractor(url, file_type).parse_async()
    except (UnsupportedFormatError, ExtractionError) as e:
        raise ValueError(str(e)) from e
    return result.text


# ─── Socket emitter ──────────────────────────────────────────────────

async def _emit_progress(user_id: uuid.UUID, kb_id: uuid.UUID, doc: Document) -> None:
    """Relay document phase/progress to the user's socket room. Best-effort."""
    try:
        from app.modules.runtime.notifications.service import notify_user

        await notify_user(
            str(user_id),
            "document:progress",
            {
                "kb_id": str(kb_id),
                "doc_id": str(doc.id),
                "status": doc.status,
                "phase": doc.processing_phase,
                "progress": doc.processing_progress,
                "chunk_count": doc.chunk_count,
                "error_message": doc.error_message,
            },
        )
    except Exception as exc:  # noqa: BLE001 — socket errors must not fail ingestion
        logger.warning("notify_user document:progress failed: %s", exc)


# ─── Main ingestion ──────────────────────────────────────────────────

from app.modules.studio.knowledge.embedding import build_for_kb


async def ingest_document(
    db: AsyncSession,
    kb: KnowledgeBase,
    document: Document,
) -> Document:
    """Full ingestion pipeline for a single document — commits between phases
    so a concurrent reader (polling fallback, page refresh) sees intermediate
    progress. Every commit is followed by a socket emit for realtime UI.
    """

    async def set_phase(
        phase: str | None,
        *,
        status: str | None = None,
        progress: int | None = None,
    ) -> None:
        document.processing_phase = phase
        if status is not None:
            document.status = status
        if progress is not None:
            document.processing_progress = progress
        await db.commit()
        await db.refresh(document)
        await _emit_progress(kb.user_id, kb.id, document)

    # Phase: parsing
    document.processing_started_at = datetime.now(timezone.utc)
    await set_phase("parsing", status="processing", progress=0)

    try:
        raw_text = await parse_document(document.file_path, document.file_type)

        if not raw_text or not raw_text.strip():
            document.error_message = (
                "Không extract được text từ file — có thể là ảnh scan hoặc "
                "font encoding không chuẩn."
            )
            document.processing_completed_at = datetime.now(timezone.utc)
            await set_phase("failed", status="failed")
            return document

        # Phase: chunking
        await set_phase("chunking")

        # Branch on KB.parent_chunk_size:
        #   == 0  legacy single-level — split into chunk_size pieces.
        #   > 0   parent-child — split twice. Parents at parent_chunk_size
        #         get NO embedding (level=1, only returned to LLM). Small
        #         children at chunk_size get the embedding + level=0 +
        #         parent_chunk_id pointing back. Searched against the
        #         small layer, returned via the parent layer.
        if kb.parent_chunk_size and kb.parent_chunk_size > kb.chunk_size:
            parent_splitter = RecursiveCharacterTextSplitter(
                chunk_size=kb.parent_chunk_size,
                # Overlap inside parents reduces context bleeding — keep
                # smaller than the parent size to leave room.
                chunk_overlap=min(kb.chunk_overlap, kb.parent_chunk_size // 10),
            )
            parent_texts = parent_splitter.split_text(raw_text)
            child_splitter = RecursiveCharacterTextSplitter(
                chunk_size=kb.chunk_size,
                chunk_overlap=kb.chunk_overlap,
            )
            # Flatten: list of (parent_index, child_text). Parents are
            # rebuilt later from parent_texts after we have UUIDs.
            chunks_with_parent: list[tuple[int, str]] = []
            for pi, parent_text in enumerate(parent_texts):
                for child_text in child_splitter.split_text(parent_text):
                    chunks_with_parent.append((pi, child_text))
            chunks = [t for _, t in chunks_with_parent]
        else:
            parent_texts = []
            chunks_with_parent = []
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=kb.chunk_size,
                chunk_overlap=kb.chunk_overlap,
            )
            chunks = splitter.split_text(raw_text)

        if not chunks:
            document.chunk_count = 0
            document.processing_completed_at = datetime.now(timezone.utc)
            await set_phase("ready", status="ready", progress=100)
            return document

        # Persist parent chunks first so children can reference their
        # IDs. Parents carry no embedding — they're only returned to
        # the LLM after a child match — so no embed call needed.
        parent_id_by_index: dict[int, uuid.UUID] = {}
        parent_records: list[DocumentChunk] = []
        for pi, ptext in enumerate(parent_texts):
            parent = DocumentChunk(
                document_id=document.id,
                knowledge_base_id=kb.id,
                workspace_id=kb.workspace_id,
                content=ptext,
                chunk_index=pi,
                chunk_level=1,
                token_count=len(ptext) // 4,
                data={
                    "source": document.filename,
                    "level": "parent",
                    "parent_index": pi,
                },
            )
            db.add(parent)
            parent_records.append(parent)
        if parent_records:
            await db.flush()
            for pi, parent in enumerate(parent_records):
                parent_id_by_index[pi] = parent.id

        # Phase: embedding (batched so we can report progress)
        await set_phase("embedding", progress=0)

        embeddings = build_for_kb(kb)
        chunk_records: list[DocumentChunk] = []

        total = len(chunks)
        done = 0
        for start in range(0, total, EMBED_BATCH_SIZE):
            batch = chunks[start : start + EMBED_BATCH_SIZE]
            vectors = await embeddings.aembed_documents(batch)

            for offset, (text, vec) in enumerate(zip(batch, vectors)):
                i = start + offset
                parent_id: uuid.UUID | None = None
                if chunks_with_parent:
                    parent_id = parent_id_by_index.get(chunks_with_parent[i][0])
                chunk_records.append(
                    DocumentChunk(
                        document_id=document.id,
                        knowledge_base_id=kb.id,
                        workspace_id=kb.workspace_id,
                        content=text,
                        embedding=vec,
                        chunk_index=i,
                        chunk_level=0,
                        parent_chunk_id=parent_id,
                        token_count=len(text) // 4,
                        data={
                            "source": document.filename,
                            "chunk_index": i,
                            "total_chunks": total,
                        },
                    )
                )

            done += len(batch)
            document.processing_progress = int(done / total * 100)
            # No commit here yet — we'll commit all chunks together at the end,
            # but emit progress so UI updates smoothly.
            await _emit_progress(kb.user_id, kb.id, document)

        # Persist chunks + final counters
        db.add_all(chunk_records)
        document.status = "ready"
        document.processing_phase = "ready"
        # ``chunk_count`` is the searchable layer — exclude parents so
        # the UI shows the user-meaningful number.
        document.chunk_count = total
        document.token_count = sum(c.token_count or 0 for c in chunk_records)
        document.processing_completed_at = datetime.now(timezone.utc)
        document.processing_progress = 100

        # Update KB counters
        result = await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == kb.id)
        )
        kb_fresh = result.scalar_one()
        kb_fresh.total_documents = (kb_fresh.total_documents or 0) + 1
        kb_fresh.total_chunks = (kb_fresh.total_chunks or 0) + total

        await db.commit()
        await db.refresh(document)
        await _emit_progress(kb.user_id, kb.id, document)
        await _notify_inbox(
            db,
            user_id=kb.user_id,
            workspace_id=kb.workspace_id,
            kb=kb,
            document=document,
            success=True,
        )
        return document

    except Exception as exc:  # noqa: BLE001
        logger.exception("ingest_document failed: %s", exc)
        document.error_message = str(exc)[:1000]
        document.processing_completed_at = datetime.now(timezone.utc)
        try:
            await set_phase("failed", status="failed")
        except Exception:  # noqa: BLE001
            # If DB rollback-needed state, try reset
            await db.rollback()
        await _notify_inbox(
            db,
            user_id=kb.user_id,
            workspace_id=kb.workspace_id,
            kb=kb,
            document=document,
            success=False,
            error=str(exc)[:500],
        )
        return document


async def _notify_inbox(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    workspace_id: uuid.UUID | None,
    kb: KnowledgeBase,
    document: Document,
    success: bool,
    error: str | None = None,
) -> None:
    """Persistent inbox row when a document finishes (good or bad).

    Why both branches: long-running KB jobs are the #1 case where
    a user closes the tab and comes back later — the WS event from
    ``_emit_progress`` is gone, so they need history to know what
    happened. Fire-and-forget; never break ingestion.
    """
    try:
        from app.models.notification import TYPE_KB_FAILED, TYPE_KB_PROCESSED
        from app.modules.runtime.notifications import inbox as inbox_service

        title = (
            f"“{document.title or document.file_path}” added to {kb.name}"
            if success
            else f"“{document.title or document.file_path}” failed to process"
        )
        await inbox_service.notify(
            db,
            user_id=user_id,
            type=TYPE_KB_PROCESSED if success else TYPE_KB_FAILED,
            title=title,
            body=None if success else (error or "Unknown error"),
            link_url=f"/knowledge/{kb.id}",
            workspace_id=workspace_id,
            extra={
                "kb_id": str(kb.id),
                "document_id": str(document.id),
                "chunk_count": document.chunk_count or 0,
            },
        )
        await db.commit()
    except Exception:  # noqa: BLE001
        logger.debug("kb notify_inbox failed", exc_info=True)


