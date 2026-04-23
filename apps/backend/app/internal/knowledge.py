"""Internal knowledge endpoints — invoked by dispatcher consumer, not users."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.knowledge.ingestion import ingest_document
from app.knowledge.service import (
    get_document,
    get_knowledge_base_unscoped,
)

router = APIRouter(prefix="/knowledge", tags=["internal:knowledge"])


class IngestRequest(BaseModel):
    kb_id: uuid.UUID
    doc_id: uuid.UUID


@router.post("/ingest")
async def ingest_endpoint(
    body: IngestRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Run ingestion pipeline for a document.

    Called asynchronously by the dispatcher consumer after a user upload.
    Idempotent: re-runs on an already-processed document will re-process it.
    """
    kb = await get_knowledge_base_unscoped(db, body.kb_id)
    doc = await get_document(db, body.doc_id)

    if not kb or not doc:
        return {"status": "skipped", "reason": "kb or doc not found"}

    await ingest_document(db, kb, doc)
    return {
        "status": doc.status,
        "phase": doc.processing_phase,
        "chunks": doc.chunk_count,
    }
