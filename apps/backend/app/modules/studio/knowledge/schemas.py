import uuid
from datetime import datetime

from pydantic import BaseModel

from app.platform.schemas.base import AppBaseModel


class KnowledgeBaseCreate(BaseModel):
    name: str
    description: str | None = None
    chunk_size: int = 1000
    chunk_overlap: int = 200
    chunk_strategy: str = "recursive"
    retrieval_top_k: int = 5
    retrieval_score_threshold: float = 0.7
    # "vector" = legacy cosine-only. "hybrid" = BM25 ∪ vector via RRF
    # (default — better recall for keyword-heavy queries).
    search_mode: str = "hybrid"
    # Reranker — null/empty = disabled. "cohere" is the only provider
    # wired today; "bge", "voyage" are roadmapped.
    rerank_provider: str | None = None
    rerank_model: str | None = None
    rerank_top_n: int = 5
    # Parent-child chunking. 0 = disabled (default; single-level
    # chunking). >0 enables — value is the parent chunk size in chars.
    parent_chunk_size: int = 0


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    chunk_size: int | None = None
    chunk_overlap: int | None = None
    retrieval_top_k: int | None = None
    retrieval_score_threshold: float | None = None
    search_mode: str | None = None
    rerank_provider: str | None = None
    rerank_model: str | None = None
    rerank_top_n: int | None = None
    parent_chunk_size: int | None = None


class KnowledgeBaseResponse(AppBaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    embedding_provider: str
    embedding_model: str
    embedding_dimensions: int
    chunk_size: int
    chunk_overlap: int
    chunk_strategy: str
    retrieval_top_k: int
    retrieval_score_threshold: float
    search_mode: str
    rerank_provider: str | None
    rerank_model: str | None
    rerank_top_n: int
    parent_chunk_size: int
    total_documents: int
    total_chunks: int
    status: str
    created_at: datetime
    updated_at: datetime


class DocumentResponse(AppBaseModel):
    __storage_fields__ = ("file_path",)

    id: uuid.UUID
    knowledge_base_id: uuid.UUID
    filename: str
    file_path: str
    file_type: str
    file_size: int | None
    chunk_count: int
    status: str
    processing_phase: str | None
    processing_progress: int | None
    error_message: str | None
    created_at: datetime


class RetrievalQuery(BaseModel):
    query: str
    top_k: int = 5


class RetrievedChunkResponse(AppBaseModel):
    content: str
    metadata: dict
    score: float | None = None


class DocumentDetailResponse(AppBaseModel):
    """Document detail — thêm snapshot của KB embedding config + linked_apps count."""

    __storage_fields__ = ("file_path",)

    id: uuid.UUID
    knowledge_base_id: uuid.UUID
    filename: str
    file_path: str
    file_type: str
    file_size: int | None
    mime_type: str | None
    content_hash: str | None
    chunk_count: int
    token_count: int | None
    status: str
    processing_phase: str | None
    processing_progress: int | None
    error_message: str | None
    processing_started_at: datetime | None
    processing_completed_at: datetime | None
    created_at: datetime

    # Snapshot từ KB để render "Technical parameters" panel
    chunk_size: int
    chunk_overlap: int
    chunk_strategy: str
    embedding_provider: str
    embedding_model: str
    embedding_dimensions: int

    # Số agent đang gắn KB chứa document này
    linked_apps: int


class ChunkResponse(AppBaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    knowledge_base_id: uuid.UUID
    chunk_index: int
    content: str
    token_count: int | None
    data: dict
    created_at: datetime


class ChunkListResponse(BaseModel):
    items: list[ChunkResponse]
    total: int
