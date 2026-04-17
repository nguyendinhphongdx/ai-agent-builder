"""Document ingestion pipeline: parse -> chunk -> embed -> store in pgvector."""
from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone

from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.knowledge_base import KnowledgeBase


class DocumentParser:
    """Parse documents into raw text based on file type."""

    @staticmethod
    def _resolve_local_path(file_path: str) -> str:
        """Resolve a storage key (kb/...) to a valid local filesystem path."""
        if os.path.isabs(file_path) and os.path.exists(file_path):
            return file_path

        if os.path.exists(file_path):
            return os.path.abspath(file_path)

        upload_path = os.path.join(settings.UPLOAD_DIR, file_path)
        if os.path.exists(upload_path):
            return os.path.abspath(upload_path)

        # Keep original path for downstream error handling with the same input.
        return file_path

    @staticmethod
    async def parse(file_path: str, file_type: str) -> str:
        local_path = DocumentParser._resolve_local_path(file_path)

        if file_type in ("txt", "md"):
            with open(local_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

        elif file_type == "pdf":
            try:
                from langchain_community.document_loaders import PyPDFLoader
                loader = PyPDFLoader(local_path)
                pages = loader.load()
                return "\n\n".join(page.page_content for page in pages)
            except ImportError:
                raise ValueError("PyPDF is required for PDF parsing. Install pypdf.")

        elif file_type == "docx":
            try:
                from langchain_community.document_loaders import Docx2txtLoader
                loader = Docx2txtLoader(local_path)
                docs = loader.load()
                return "\n\n".join(doc.page_content for doc in docs)
            except ImportError:
                raise ValueError("docx2txt is required for DOCX parsing.")

        elif file_type == "csv":
            with open(local_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

        elif file_type == "html":
            try:
                from langchain_community.document_loaders import BSHTMLLoader
                loader = BSHTMLLoader(local_path)
                docs = loader.load()
                return "\n\n".join(doc.page_content for doc in docs)
            except ImportError:
                with open(local_path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()

        else:
            with open(local_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()


from app.knowledge.embeddings import build_embeddings

async def ingest_document(
    db: AsyncSession,
    kb: KnowledgeBase,
    document: Document,
) -> Document:
    """Full ingestion pipeline for a single document."""
    document.status = "processing"
    document.processing_started_at = datetime.now(timezone.utc)
    await db.flush()

    try:
        # 1. Parse
        raw_text = await DocumentParser.parse(document.file_path, document.file_type)

        # 2. Chunk
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=kb.chunk_size,
            chunk_overlap=kb.chunk_overlap,
        )
        chunks = splitter.split_text(raw_text)

        if not chunks:
            document.status = "ready"
            document.chunk_count = 0
            document.processing_completed_at = datetime.now(timezone.utc)
            await db.flush()
            return document

        # 3. Embed
        embeddings = build_embeddings()
        vectors = await embeddings.aembed_documents(chunks)

        # 4. Store chunks with embeddings
        chunk_records = []
        for i, (text, vec) in enumerate(zip(chunks, vectors)):
            chunk = DocumentChunk(
                document_id=document.id,
                knowledge_base_id=kb.id,
                content=text,
                embedding=vec,
                chunk_index=i,
                token_count=len(text) // 4,  # rough estimate
                data={
                    "source": document.filename,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                },
            )
            chunk_records.append(chunk)

        db.add_all(chunk_records)

        # 5. Update document status
        document.status = "ready"
        document.chunk_count = len(chunks)
        document.token_count = sum(c.token_count or 0 for c in chunk_records)
        document.processing_completed_at = datetime.now(timezone.utc)

        # 6. Update KB counters
        result = await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == kb.id)
        )
        kb_fresh = result.scalar_one()
        kb_fresh.total_documents = (kb_fresh.total_documents or 0) + 1
        kb_fresh.total_chunks = (kb_fresh.total_chunks or 0) + len(chunks)

        await db.flush()
        await db.refresh(document)
        return document

    except Exception as e:
        document.status = "failed"
        document.error_message = str(e)[:1000]
        document.processing_completed_at = datetime.now(timezone.utc)
        await db.flush()
        return document


def compute_file_hash(file_path: str) -> str:
    """Compute SHA-256 hash of a file."""
    local_path = DocumentParser._resolve_local_path(file_path)
    sha256 = hashlib.sha256()
    with open(local_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()
