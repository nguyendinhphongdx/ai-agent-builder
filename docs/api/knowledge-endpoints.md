---
id: api-knowledge-endpoints
title: Knowledge Base API Endpoints
domain: api
tags: [knowledge, rag, documents, upload, embeddings, retrieval, pgvector]
related: [api-agent-endpoints, flows-document-upload]
summary: Documents Knowledge Base CRUD, document upload (multipart), and semantic query endpoints with request/response examples.
---

# Knowledge Base API Endpoints

**Router:** `app/knowledge/router.py`  
**Prefix:** `/api/knowledge-bases`  
**Auth:** All endpoints require `get_current_user`.

## Knowledge Base CRUD

### GET /knowledge-bases

List all knowledge bases owned by the current user.

**Response (200):** `KnowledgeBaseResponse[]`

### POST /knowledge-bases

Create a new knowledge base.

**Request:**
```json
{ "name": "Product Docs", "description": "Product documentation" }
```

**Response (201):** `KnowledgeBaseResponse`

### GET /knowledge-bases/{kb_id}

Get knowledge base detail.

**Errors:** 404 if not found or not owned.

### PUT /knowledge-bases/{kb_id}

Update knowledge base metadata. Partial update via `exclude_unset`.

### DELETE /knowledge-bases/{kb_id}

Delete a knowledge base.

**Response:** 204 No Content.

## Document Management

### POST /knowledge-bases/{kb_id}/documents

Upload a document file (multipart form data).

**Request:** `file` field as `UploadFile`.

**Allowed extensions:** `pdf`, `txt`, `md`, `docx`, `csv`, `html`

**Processing pipeline (synchronous):**

1. Validates file extension against allowed set
2. Saves file to storage at `kb/{kb_id}/` path
3. Computes SHA-256 content hash
4. Creates Document record with status `"pending"`
5. Runs `ingest_document()` pipeline (parse -> chunk -> embed -> store)
6. Returns document with final status

**Response (201):**
```json
{
  "id": "uuid", "filename": "guide.pdf", "file_type": "pdf",
  "file_size": 1048576, "status": "ready", "chunk_count": 42,
  "token_count": 8500, "created_at": "..."
}
```

**Errors:** 400 if unsupported file type.

### GET /knowledge-bases/{kb_id}/documents

List all documents in a knowledge base.

**Response (200):** `DocumentResponse[]`

### DELETE /knowledge-bases/{kb_id}/documents/{doc_id}

Delete a document and its storage file.

**Response:** 204 No Content.

## Semantic Query

### POST /knowledge-bases/{kb_id}/query

Search the knowledge base using semantic similarity.

**Request:**
```json
{ "query": "How do I reset my password?", "top_k": 5 }
```

**Response (200):**
```json
[
  {
    "content": "To reset your password, navigate to Settings > Security...",
    "metadata": {"source": "guide.pdf", "chunk_index": 7, "total_chunks": 42},
    "score": 0.89
  }
]
```

Uses `KnowledgeRetriever` which performs pgvector similarity search across all chunks in the knowledge base.
