import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.base import AppBaseModel


class KnowledgeBaseCreate(BaseModel):
    name: str
    description: str | None = None
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    chunk_size: int = 1000
    chunk_overlap: int = 200
    chunk_strategy: str = "recursive"
    retrieval_top_k: int = 5
    retrieval_score_threshold: float = 0.7


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    chunk_size: int | None = None
    chunk_overlap: int | None = None
    retrieval_top_k: int | None = None
    retrieval_score_threshold: float | None = None


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
    error_message: str | None
    created_at: datetime


class RetrievalQuery(BaseModel):
    query: str
    top_k: int = 5


class RetrievedChunkResponse(AppBaseModel):
    content: str
    metadata: dict
    score: float | None = None
