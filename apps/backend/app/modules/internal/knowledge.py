"""Internal knowledge endpoints — invoked by dispatcher consumer, not users."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ingestion import ingest_document
from app.modules.jobs import service as job_service
from app.modules.knowledge.service import (
    get_document,
    get_knowledge_base_unscoped,
)
from app.platform.db.session import get_db

logger = logging.getLogger("agentforge")
router = APIRouter(prefix="/knowledge", tags=["internal:knowledge"])


class IngestRequest(BaseModel):
    kb_id: uuid.UUID
    doc_id: uuid.UUID
    # Injected by app.modules.jobs.producer.enqueue — lets this handler walk
    # the Job row through running → completed/dead. Optional for
    # legacy dispatcher calls that bypassed the producer.
    job_id: uuid.UUID | None = None
    # Carried for visibility but not used by the pipeline (reprocess
    # just resets doc state before re-ingesting).
    reprocess: bool | None = None


@router.post("/ingest")
async def ingest_endpoint(
    body: IngestRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Run ingestion pipeline for a document.

    Updates the linked Job row through its lifecycle (running →
    completed / failed / dead) so the dashboard reflects state.
    """
    kb = await get_knowledge_base_unscoped(db, body.kb_id)
    doc = await get_document(db, body.doc_id)

    job = await job_service.get_job(db, body.job_id) if body.job_id else None

    if not kb or not doc:
        if job is not None:
            await job_service.mark_dead(db, job, error="kb or doc not found")
            await db.commit()
        return {"status": "skipped", "reason": "kb or doc not found"}

    if job is not None:
        await job_service.mark_running(db, job)
        await db.commit()

    try:
        await ingest_document(db, kb, doc)
    except Exception as exc:
        logger.exception("kb.ingest failed for doc=%s", body.doc_id)
        if job is not None:
            # Dispatcher retries up to maxAttempts; if we've hit the
            # ceiling on this attempt, mark dead so DLQ surfaces it.
            terminal = job.attempt >= job.max_attempts
            if terminal:
                await job_service.mark_dead(db, job, error=str(exc))
            else:
                await job_service.mark_failed(db, job, error=str(exc))
            await db.commit()
        raise

    if job is not None:
        await job_service.mark_completed(
            db,
            job,
            result={
                "status": doc.status,
                "phase": doc.processing_phase,
                "chunks": doc.chunk_count,
            },
        )
        await db.commit()

    return {
        "status": doc.status,
        "phase": doc.processing_phase,
        "chunks": doc.chunk_count,
    }
