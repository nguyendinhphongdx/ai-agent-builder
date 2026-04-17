---
id: table-knowledge
title: "Tables: knowledge_bases, documents, document_chunks"
domain: database
tags: [knowledge-base, rag, embedding, pgvector, chunking, schema]
related: [schema-overview, table-agents, storage, agent-executor]
summary: Three-table knowledge pipeline -- knowledge base configuration, uploaded documents with processing status, and pgvector-embedded chunks for semantic search.
---

# Knowledge Base Tables

Source: `apps/backend/app/models/knowledge_base.py`, `document.py`, `document_chunk.py`

## Table: knowledge_bases

Inherits: `Base`, `UUIDMixin`, `TimestampMixin`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | no | `uuid4()` | PK |
| `user_id` | `UUID` | no | -- | FK(`users.id`) CASCADE, INDEX |
| `name` | `String(255)` | no | -- | Display name. |
| `description` | `Text` | yes | `NULL` | |
| `embedding_provider` | `String(50)` | no | `"openai"` | Embedding API provider. |
| `embedding_model` | `String(100)` | no | `"text-embedding-3-small"` | Model used for vectorization. |
| `embedding_dimensions` | `Integer` | no | `1536` | Vector dimensionality. |
| `chunk_size` | `Integer` | no | `1000` | Characters per chunk. |
| `chunk_overlap` | `Integer` | no | `200` | Overlap characters between consecutive chunks. |
| `chunk_strategy` | `String(50)` | no | `"recursive"` | `"recursive"` or `"character"`. |
| `retrieval_top_k` | `Integer` | no | `5` | Number of chunks returned per query. |
| `retrieval_score_threshold` | `Float` | no | `0.7` | Minimum cosine similarity score. |
| `total_documents` | `Integer` | no | `0` | Counter cache. |
| `total_chunks` | `Integer` | no | `0` | Counter cache. |
| `status` | `String(20)` | no | `"active"` | |

## Table: documents

Inherits: `Base`, `UUIDMixin` (no TimestampMixin -- has custom `created_at`)

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | no | `uuid4()` | PK |
| `knowledge_base_id` | `UUID` | no | -- | FK(`knowledge_bases.id`) CASCADE, INDEX |
| `filename` | `String(512)` | no | -- | Original upload filename. |
| `file_path` | `String(1024)` | no | -- | Server-side storage path (from `save_upload`). |
| `file_type` | `String(20)` | no | -- | Extension: `"pdf"`, `"txt"`, `"docx"`. |
| `file_size` | `BigInteger` | yes | `NULL` | Size in bytes. |
| `mime_type` | `String(100)` | yes | `NULL` | MIME type string. |
| `content_hash` | `String(64)` | yes | `NULL` | SHA-256 hash for deduplication. |
| `chunk_count` | `Integer` | no | `0` | Number of chunks produced. |
| `token_count` | `Integer` | yes | `NULL` | Total tokens in the document. |
| `status` | `String(20)` | no | `"pending"` | `"pending"` -> `"processing"` -> `"completed"` / `"failed"` |
| `error_message` | `Text` | yes | `NULL` | Error details if status is `"failed"`. |
| `metadata` | `JSONB` | no | `{}` | Arbitrary metadata (page count, author, etc.). |
| `processing_started_at` | `TIMESTAMP(tz)` | yes | `NULL` | |
| `processing_completed_at` | `TIMESTAMP(tz)` | yes | `NULL` | |
| `created_at` | `TIMESTAMP(tz)` | no | `now()` | |

## Table: document_chunks

Inherits: `Base`, `UUIDMixin` (custom `created_at`)

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | no | `uuid4()` | PK |
| `document_id` | `UUID` | no | -- | FK(`documents.id`) CASCADE, INDEX |
| `knowledge_base_id` | `UUID` | no | -- | FK(`knowledge_bases.id`) CASCADE, INDEX. Denormalized for fast retrieval queries. |
| `chunk_index` | `Integer` | no | -- | Ordinal position within the source document. |
| `content` | `Text` | no | -- | Plain text content of the chunk. |
| `token_count` | `Integer` | yes | `NULL` | Token count for this chunk. |
| `embedding` | `Vector(1536)` | yes | `NULL` | pgvector column for semantic search. |
| `metadata` | `JSONB` | no | `{}` | Source metadata: page number, section heading, etc. |
| `created_at` | `TIMESTAMP(tz)` | no | `now()` | |

## Chunk Metadata Example

```json
{
  "page": 3,
  "section": "Introduction",
  "source_filename": "report.pdf"
}
```

## Relationships

- `knowledge_bases` 1:N `documents` (cascade delete-orphan)
- `documents` 1:N `document_chunks` (cascade delete-orphan)
- `document_chunks` N:1 `knowledge_bases` (denormalized shortcut)

## pgvector Usage

The `embedding` column uses the `Vector(1536)` type from `pgvector.sqlalchemy`. Retrieval queries use cosine similarity against this column, filtered by `knowledge_base_id` and thresholded by `retrieval_score_threshold`.
