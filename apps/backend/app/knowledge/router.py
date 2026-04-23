import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.knowledge.ingestion import ingest_document
from app.knowledge.retriever import KnowledgeRetriever
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
    update_knowledge_base,
)
from app.models.document import Document
from app.models.user import User
from app.storage import get_storage, generate_storage_key

router = APIRouter(prefix="/knowledge-bases", tags=["knowledge-bases"])

ALLOWED_EXTENSIONS = {"pdf", "txt", "md", "docx", "csv", "html"}


@router.get("", response_model=list[KnowledgeBaseResponse])
async def list_kbs_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    kbs = await list_knowledge_bases(db, current_user.id)
    return [KnowledgeBaseResponse.model_validate(kb).release() for kb in kbs]


@router.post("", response_model=KnowledgeBaseResponse, status_code=status.HTTP_201_CREATED)
async def create_kb_endpoint(
    body: KnowledgeBaseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    kb = await create_knowledge_base(db, current_user.id, **body.model_dump())
    return KnowledgeBaseResponse.model_validate(kb).release()


@router.get("/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_kb_endpoint(
    kb_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    kb = await get_knowledge_base(db, kb_id, current_user.id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return KnowledgeBaseResponse.model_validate(kb).release()


@router.put("/{kb_id}", response_model=KnowledgeBaseResponse)
async def update_kb_endpoint(
    kb_id: uuid.UUID,
    body: KnowledgeBaseUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    kb = await get_knowledge_base(db, kb_id, current_user.id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    kb = await update_knowledge_base(db, kb, **body.model_dump(exclude_unset=True))
    return KnowledgeBaseResponse.model_validate(kb).release()


@router.delete("/{kb_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_kb_endpoint(
    kb_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    kb = await get_knowledge_base(db, kb_id, current_user.id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    await delete_knowledge_base(db, kb)


# --- Documents ---


@router.post("/{kb_id}/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document_endpoint(
    kb_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    kb = await get_knowledge_base(db, kb_id, current_user.id)
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

    # Create document record
    doc = Document(
        knowledge_base_id=kb_id,
        filename=file.filename or "unknown",
        file_path=storage_key,
        file_type=ext,
        file_size=len(content),
        mime_type=file.content_type,
        content_hash=content_hash,
        status="pending",
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)

    # Run ingestion (synchronous for now, could be background task later)
    doc = await ingest_document(db, kb, doc)

    return DocumentResponse.model_validate(doc).release()


@router.get("/{kb_id}/documents", response_model=list[DocumentResponse])
async def list_documents_endpoint(
    kb_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    kb = await get_knowledge_base(db, kb_id, current_user.id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    docs = await list_documents(db, kb_id)
    return [DocumentResponse.model_validate(d).release() for d in docs]


@router.get("/{kb_id}/documents/{doc_id}", response_model=DocumentDetailResponse)
async def get_document_detail_endpoint(
    kb_id: uuid.UUID,
    doc_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Detail endpoint for a document — includes snapshot of KB settings for the right-panel."""
    kb = await get_knowledge_base(db, kb_id, current_user.id)
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List chunks for a document (paginated)."""
    kb = await get_knowledge_base(db, kb_id, current_user.id)
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


@router.delete("/{kb_id}/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document_endpoint(
    kb_id: uuid.UUID,
    doc_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    kb = await get_knowledge_base(db, kb_id, current_user.id)
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    kb = await get_knowledge_base(db, kb_id, current_user.id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    retriever = KnowledgeRetriever(db)
    chunks = await retriever.retrieve(body.query, [kb_id], body.top_k)

    return [
        RetrievedChunkResponse(content=c.content, metadata=c.metadata, score=c.score).release()
        for c in chunks
    ]
