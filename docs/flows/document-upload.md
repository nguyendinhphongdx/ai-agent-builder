---
id: flows-document-upload
title: Document Upload and Ingestion Flow
domain: flows
tags: [knowledge, upload, parsing, chunking, embeddings, pgvector, rag]
related: [api-knowledge-endpoints, frontend-feature-agents-editor]
summary: End-to-end flow from file upload through storage, parsing, chunking, embedding with OpenAI, and storing vectors in pgvector.
---

# Document Upload and Ingestion Flow

## Overview

User uploads a document to a knowledge base. The system saves the file, parses it, chunks the text, generates embeddings via OpenAI, and stores the vectors in pgvector for similarity search.

## Step-by-Step

### 1. Upload File

**Frontend:** User drags or browses a file in `KnowledgeUploadSection`.

Accepted formats: PDF, TXT, MD, DOCX, CSV, HTML.

**API call:**

```
POST /api/knowledge-bases/{kb_id}/documents
Content-Type: multipart/form-data
Body: file=<upload>
```

### 2. Validate File Type

Backend extracts file extension and checks against allowed set: `{pdf, txt, md, docx, csv, html}`. Returns 400 for unsupported types.

### 3. Save to Storage

```python
file_path, file_size = await save_upload(file, f"kb/{kb_id}")
```

File saved to the storage directory under `kb/{kb_id}/` path.

### 4. Compute Content Hash

```python
content_hash = compute_file_hash(file_path)  # SHA-256
```

SHA-256 hash computed by reading file in 8KB chunks.

### 5. Create Document Record

Document created in DB with `status: "pending"`, file metadata (filename, path, type, size, mime type, hash).

### 6. Ingestion Pipeline (`ingest_document`)

Status transitions: `pending` -> `processing` -> `ready` or `failed`.

#### 6a. Parse

`DocumentParser.parse(file_path, file_type)`:

| File Type | Parser                          |
|-----------|---------------------------------|
| txt, md   | Direct `open()` read            |
| pdf       | `PyPDFLoader` from langchain    |
| docx      | `Docx2txtLoader` from langchain |
| csv       | Direct `open()` read            |
| html      | `BSHTMLLoader` or fallback read |

Returns raw text content.

#### 6b. Chunk

Uses `RecursiveCharacterTextSplitter` from langchain_text_splitters:

- `chunk_size`: from knowledge base config (e.g., 1000)
- `chunk_overlap`: from knowledge base config (e.g., 200)

Splits text into overlapping chunks for context preservation.

#### 6c. Embed

```python
embeddings = OpenAIEmbeddings(model=kb.embedding_model, dimensions=kb.embedding_dimensions)
vectors = await embeddings.aembed_documents(chunks)
```

Generates vector embeddings for all chunks in a batch call to OpenAI.

#### 6d. Store Chunks

Creates `DocumentChunk` records with:
- `content`: chunk text
- `embedding`: vector (stored in pgvector column)
- `chunk_index`: position in document
- `token_count`: rough estimate (`len(text) // 4`)
- `metadata`: `{ source, chunk_index, total_chunks }`

All chunks added to DB in batch.

### 7. Update Counters

- Document: `status: "ready"`, `chunk_count`, `token_count`, `processing_completed_at`
- Knowledge base: increments `total_documents` and `total_chunks`

### 8. Return Response

API returns `DocumentResponse` with final status and counts.

## Error Handling

If any step in the pipeline fails:
- Document status set to `"failed"`
- `error_message` populated (truncated to 1000 chars)
- `processing_completed_at` set
- Error does not propagate -- document record persists with failure state

## Frontend Status Tracking

`KnowledgeUploadSection` shows per-file status:
- **uploading**: progress bar
- **processing**: "Processing chunks & embeddings..." with spinner
- **ready**: green check icon
- **failed**: red alert icon
