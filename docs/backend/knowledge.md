---
id: backend-knowledge
title: Knowledge Bases
domain: backend
tags: [knowledge, rag, embedding, pgvector, chunking, ingestion]
related: [backend-agents, backend-database, backend-config]
summary: KnowledgeBase and Document models, ingestion pipeline (parse, chunk, embed, store), and cosine similarity retrieval via pgvector.
---

# Knowledge Bases

## Overview

Knowledge bases provide RAG (Retrieval-Augmented Generation) capabilities for
agents. Documents are uploaded, parsed into text, split into chunks, embedded
into vectors, and stored in PostgreSQL via pgvector. At query time, a cosine
similarity search retrieves the most relevant chunks.

## Specification

### KnowledgeBase Model

Table: `knowledge_bases`. Inherits `UUIDMixin` + `TimestampMixin`.

| Column | Type | Default | Description |
|---|---|---|---|
| `user_id` | `UUID` FK -> users | required | Owner |
| `name` | `String(255)` | required | Display name |
| `description` | `Text` | `None` | Optional description |
| `embedding_provider` | `String(50)` | `"openai"` | Embedding API provider |
| `embedding_model` | `String(100)` | `"text-embedding-3-small"` | Embedding model name |
| `embedding_dimensions` | `Integer` | `1536` | Vector dimensions |
| `chunk_size` | `Integer` | `1000` | Characters per chunk |
| `chunk_overlap` | `Integer` | `200` | Overlap characters between chunks |
| `chunk_strategy` | `String(50)` | `"recursive"` | Splitting strategy |
| `retrieval_top_k` | `Integer` | `5` | Number of chunks returned per query |
| `retrieval_score_threshold` | `Float` | `0.7` | Minimum similarity score |
| `total_documents` | `Integer` | `0` | Counter |
| `total_chunks` | `Integer` | `0` | Counter |
| `status` | `String(20)` | `"active"` | KB status |

### Document Model

Table: `documents`. Inherits `UUIDMixin`.

| Column | Type | Default | Description |
|---|---|---|---|
| `knowledge_base_id` | `UUID` FK | required | Parent KB |
| `filename` | `String(512)` | required | Original filename |
| `file_path` | `String(1024)` | required | Server storage path |
| `file_type` | `String(20)` | required | `"pdf"`, `"txt"`, `"md"`, `"docx"`, `"csv"`, `"html"` |
| `file_size` | `BigInteger` | `None` | Size in bytes |
| `mime_type` | `String(100)` | `None` | MIME type |
| `content_hash` | `String(64)` | `None` | SHA-256 hash for deduplication |
| `chunk_count` | `Integer` | `0` | Chunks produced |
| `token_count` | `Integer` | `None` | Estimated total tokens |
| `status` | `String(20)` | `"pending"` | `"pending"` -> `"processing"` -> `"ready"` / `"failed"` |
| `error_message` | `Text` | `None` | Error detail on failure |

### DocumentChunk Model

Table: `document_chunks`. Inherits `UUIDMixin`.

| Column | Type | Description |
|---|---|---|
| `document_id` | `UUID` FK | Parent document |
| `knowledge_base_id` | `UUID` FK | Denormalized for fast queries |
| `chunk_index` | `Integer` | Position within document |
| `content` | `Text` | Chunk text |
| `token_count` | `Integer` | Estimated tokens (`len(text) // 4`) |
| `embedding` | `Vector(1536)` | pgvector column |
| `metadata` | `JSONB` | `{ source, chunk_index, total_chunks }` |

### Ingestion Pipeline (`ingest_document`)

1. **Parse** -- `DocumentParser.parse(file_path, file_type)` extracts raw text.
   - `txt`, `md`, `csv`: direct file read.
   - `pdf`: `PyPDFLoader` from langchain_community.
   - `docx`: `Docx2txtLoader` from langchain_community.
   - `html`: `BSHTMLLoader` (falls back to raw read).
   - Unknown types: raw UTF-8 read.
2. **Chunk** -- `RecursiveCharacterTextSplitter(chunk_size, chunk_overlap)`.
3. **Embed** -- `OpenAIEmbeddings(model, dimensions)` via `aembed_documents`.
4. **Store** -- Bulk insert `DocumentChunk` records with embeddings.
5. **Update counters** -- Increment `total_documents` and `total_chunks` on the KB.
6. **Error handling** -- On failure, sets `status="failed"` and stores error message.

### Retriever (`KnowledgeRetriever`)

```python
retriever = KnowledgeRetriever(db)
chunks = await retriever.retrieve(query, knowledge_base_ids, top_k=5)
```

- Embeds query with `OpenAIEmbeddings(model="text-embedding-3-small")`.
- Executes pgvector cosine distance search: `embedding.cosine_distance(query_embedding)`.
- Filters by `knowledge_base_id IN (...)` and `embedding IS NOT NULL`.
- Orders by ascending distance, limits to `top_k`.
- Returns `RetrievedChunk(content, metadata, score)` where `score = 1.0 - distance`.

### File Hashing

`compute_file_hash(file_path) -> str` computes SHA-256 for deduplication.

## File Structure

```
apps/backend/app/modules/studio/knowledge/
  __init__.py
  router.py          # FastAPI endpoints
  schemas.py         # KB/Document create/update/response schemas
  service.py         # CRUD for KBs and documents
apps/backend/app/core/
  ingestion.py       # DocumentParser, ingest_document, compute_file_hash
  retrieval.py       # KnowledgeRetriever, RetrievedChunk
  kb_connectors/     # external sync (Drive, Notion, S3, etc.)
apps/backend/app/modules/integrations/connectors/kb/
                     # router/service for managing KB connector instances
apps/backend/app/models/
  knowledge_base.py  # KnowledgeBase ORM model
  document.py        # Document ORM model
  document_chunk.py  # DocumentChunk ORM model (pgvector)
```

## Key Functions / Classes

| Symbol | File | Purpose |
|---|---|---|
| `DocumentParser` | `ingestion.py` | Static parser dispatching on file_type |
| `ingest_document` | `ingestion.py` | Full pipeline: parse -> chunk -> embed -> store |
| `compute_file_hash` | `ingestion.py` | SHA-256 of file |
| `KnowledgeRetriever` | `retriever.py` | Cosine similarity search |
| `RetrievedChunk` | `retriever.py` | Dataclass for search results |

## Examples

```python
# Ingesting a document
document = await ingest_document(db, knowledge_base, document_record)
# document.status is now "ready" or "failed"

# Querying
retriever = KnowledgeRetriever(db)
results = await retriever.retrieve("How do I reset my password?", [kb.id], top_k=3)
for chunk in results:
    print(chunk.score, chunk.content[:100])
```

### Constraints

- Embedding provider currently only supports `"openai"`. Other providers fall back to OpenAI.
- `embedding_dimensions` MUST match the model's output dimensions (1536 for text-embedding-3-small).
- `chunk_size` and `chunk_overlap` are in characters, not tokens.
- Document status transitions MUST follow: `pending -> processing -> ready|failed`.
- The `DocumentChunk.embedding` column uses pgvector `Vector(1536)`.
