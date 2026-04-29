import logging
import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.config import settings
from app.db.session import get_db
from app.dispatcher_client import dispatcher
from app.knowledge.retriever import KnowledgeRetriever

logger = logging.getLogger("agentforge")
from app.knowledge.schemas import (
    ChunkListResponse,
    ChunkResponse,
    DocumentDetailResponse,
    DocumentResponse,
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdate,
    RetrievalQuery,
    RetrievedChunkResponse,
)
from app.knowledge.service import (
    count_agents_using_kb,
    create_knowledge_base,
    delete_document,
    delete_knowledge_base,
    get_document,
    get_knowledge_base,
    list_chunks,
    list_documents,
    list_knowledge_bases,
    reset_document_for_reprocess,
    update_knowledge_base,
)
from app.models.document import Document
from app.storage import generate_storage_key, get_storage

router = APIRouter(
    prefix="/knowledge-bases",
    tags=["knowledge-bases"],
    dependencies=[Depends(get_current_user)],
)

ALLOWED_EXTENSIONS = {"pdf", "txt", "md", "docx", "csv", "html"}


@router.get("", response_model=list[KnowledgeBaseResponse])
async def list_kbs_endpoint(
    db: AsyncSession = Depends(get_db),
):
    kbs = await list_knowledge_bases(db)
    return [KnowledgeBaseResponse.model_validate(kb).release() for kb in kbs]


@router.post("", response_model=KnowledgeBaseResponse, status_code=status.HTTP_201_CREATED)
async def create_kb_endpoint(
    body: KnowledgeBaseCreate,
    db: AsyncSession = Depends(get_db),
):
    kb = await create_knowledge_base(db, **body.model_dump())
    return KnowledgeBaseResponse.model_validate(kb).release()


@router.get("/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_kb_endpoint(
    kb_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    kb = await get_knowledge_base(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return KnowledgeBaseResponse.model_validate(kb).release()


@router.put("/{kb_id}", response_model=KnowledgeBaseResponse)
async def update_kb_endpoint(
    kb_id: uuid.UUID,
    body: KnowledgeBaseUpdate,
    db: AsyncSession = Depends(get_db),
):
    kb = await get_knowledge_base(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    kb = await update_knowledge_base(db, kb, **body.model_dump(exclude_unset=True))
    return KnowledgeBaseResponse.model_validate(kb).release()


@router.delete("/{kb_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_kb_endpoint(
    kb_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    kb = await get_knowledge_base(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    await delete_knowledge_base(db, kb)


# --- Documents ---


@router.post("/{kb_id}/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document_endpoint(
    kb_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    kb = await get_knowledge_base(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    # Validate file type
    ext = os.path.splitext(file.filename or "")[1].lstrip(".").lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Save file via storage backend
    import hashlib
    storage = get_storage()
    content = await file.read()
    storage_key = generate_storage_key("kb", str(kb_id), file.filename or "file")
    await storage.upload(storage_key, content, file.content_type or "application/octet-stream")
    content_hash = hashlib.sha256(content).hexdigest()

    # Create document record — pending, no phase set yet.
    doc = Document(
        knowledge_base_id=kb_id,
        filename=file.filename or "unknown",
        file_path=storage_key,
        file_type=ext,
        file_size=len(content),
        mime_type=file.content_type,
        content_hash=content_hash,
        status="pending",
        processing_phase="queued",
        processing_progress=0,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    await db.commit()  # persist before background task picks it up

    # Enqueue ingestion via dispatcher — persistent + retry + DLQ.
    # Dispatcher consumer will POST to /api/internal/knowledge/ingest.
    # Progress is surfaced via `document:progress` socket events.
    await dispatcher.enqueue(
        "backend",
        f"{settings.API_PREFIX}/internal/knowledge/ingest",
        event="document.ingest",
        body={"kb_id": str(kb_id), "doc_id": str(doc.id)},
        priority="normal",
        retry={"maxAttempts": 3, "backoffMs": 3_000, "backoffMultiplier": 2},
        correlation_id=str(doc.id),
        timeout_ms=600_000,  # ingestion can be long (large PDF + embed)
    )

    return DocumentResponse.model_validate(doc).release()


@router.get("/{kb_id}/documents", response_model=list[DocumentResponse])
async def list_documents_endpoint(
    kb_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    kb = await get_knowledge_base(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    docs = await list_documents(db, kb_id)
    return [DocumentResponse.model_validate(d).release() for d in docs]


@router.get("/{kb_id}/documents/{doc_id}", response_model=DocumentDetailResponse)
async def get_document_detail_endpoint(
    kb_id: uuid.UUID,
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Detail endpoint for a document — includes snapshot of KB settings for the right-panel."""
    kb = await get_knowledge_base(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    doc = await get_document(db, doc_id)
    if not doc or doc.knowledge_base_id != kb_id:
        raise HTTPException(status_code=404, detail="Document not found")

    linked_apps = await count_agents_using_kb(db, kb_id)

    return DocumentDetailResponse.model_validate(
        {
            # Document fields
            "id": doc.id,
            "knowledge_base_id": doc.knowledge_base_id,
            "filename": doc.filename,
            "file_path": doc.file_path,
            "file_type": doc.file_type,
            "file_size": doc.file_size,
            "mime_type": doc.mime_type,
            "content_hash": doc.content_hash,
            "chunk_count": doc.chunk_count,
            "token_count": doc.token_count,
            "status": doc.status,
            "processing_phase": doc.processing_phase,
            "processing_progress": doc.processing_progress,
            "error_message": doc.error_message,
            "processing_started_at": doc.processing_started_at,
            "processing_completed_at": doc.processing_completed_at,
            "created_at": doc.created_at,
            # KB snapshot
            "chunk_size": kb.chunk_size,
            "chunk_overlap": kb.chunk_overlap,
            "chunk_strategy": kb.chunk_strategy,
            "embedding_provider": kb.embedding_provider,
            "embedding_model": kb.embedding_model,
            "embedding_dimensions": kb.embedding_dimensions,
            # Aggregates
            "linked_apps": linked_apps,
        }
    ).release()


@router.get("/{kb_id}/documents/{doc_id}/chunks", response_model=ChunkListResponse)
async def list_chunks_endpoint(
    kb_id: uuid.UUID,
    doc_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List chunks for a document (paginated)."""
    kb = await get_knowledge_base(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    doc = await get_document(db, doc_id)
    if not doc or doc.knowledge_base_id != kb_id:
        raise HTTPException(status_code=404, detail="Document not found")

    chunks, total = await list_chunks(db, doc_id, limit=limit, offset=offset)
    return ChunkListResponse(
        items=[ChunkResponse.model_validate(c) for c in chunks],
        total=total,
    )


@router.post("/{kb_id}/documents/{doc_id}/reprocess", response_model=DocumentResponse)
async def reprocess_document_endpoint(
    kb_id: uuid.UUID,
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retry ingestion for a document — resets its state and re-enqueues.

    Safe to call regardless of current phase: clears prior chunks, rolls back
    KB counters, resets status to pending, then hands off to the dispatcher
    queue like a fresh upload. Progress is surfaced via `document:progress`
    socket events like normal ingestion.
    """
    kb = await get_knowledge_base(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    doc = await get_document(db, doc_id)
    if not doc or doc.knowledge_base_id != kb_id:
        raise HTTPException(status_code=404, detail="Document not found")

    doc = await reset_document_for_reprocess(db, doc)
    await db.commit()

    await dispatcher.enqueue(
        "backend",
        f"{settings.API_PREFIX}/internal/knowledge/ingest",
        event="document.reprocess",
        body={"kb_id": str(kb_id), "doc_id": str(doc.id)},
        priority="normal",
        retry={"maxAttempts": 3, "backoffMs": 3_000, "backoffMultiplier": 2},
        correlation_id=str(doc.id),
        timeout_ms=600_000,
    )

    return DocumentResponse.model_validate(doc).release()


@router.delete("/{kb_id}/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document_endpoint(
    kb_id: uuid.UUID,
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    kb = await get_knowledge_base(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    doc = await get_document(db, doc_id)
    if not doc or doc.knowledge_base_id != kb_id:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete file from storage
    storage = get_storage()
    await storage.delete(doc.file_path)
    await delete_document(db, doc)


# --- Retrieval ---


@router.post("/{kb_id}/query", response_model=list[RetrievedChunkResponse])
async def query_kb_endpoint(
    kb_id: uuid.UUID,
    body: RetrievalQuery,
    db: AsyncSession = Depends(get_db),
):
    kb = await get_knowledge_base(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    retriever = KnowledgeRetriever(db)
    chunks = await retriever.retrieve(body.query, [kb_id], body.top_k)

    return [
        RetrievedChunkResponse(content=c.content, metadata=c.metadata, score=c.score).release()
        for c in chunks
    ]
