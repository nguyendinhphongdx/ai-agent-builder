---
id: storage
title: File Storage
domain: backend
tags: [storage, upload, filesystem]
related: [table-knowledge]
summary: Local filesystem storage layer for uploaded files with UUID-based naming and subdirectory organization.
---

# File Storage

Source: `apps/backend/app/storage/base.py`

## Overview

The storage module provides a minimal local filesystem abstraction for handling file uploads. It is used primarily by the knowledge base document ingestion pipeline to persist uploaded files before they are chunked and embedded.

## Configuration

The base upload directory is read from `settings.UPLOAD_DIR`. All files are stored under subdirectories within this path.

## Functions

### `save_upload(file, subdirectory) -> (file_path, file_size)`

Saves a FastAPI `UploadFile` to local storage.

**Process:**

1. Constructs the target directory as `{UPLOAD_DIR}/{subdirectory}` and creates it if it does not exist (`os.makedirs` with `exist_ok=True`).
2. Generates a unique filename by combining a `uuid4` hex string with the original file extension (extracted via `os.path.splitext`).
3. Reads the file in 8192-byte chunks and writes them to disk, accumulating the total file size.
4. Returns a tuple of `(absolute_file_path, file_size_in_bytes)`.

**Example:**

```python
path, size = await save_upload(upload_file, "knowledge_bases/abc123")
# path = "/data/uploads/knowledge_bases/abc123/a1b2c3d4e5f6.pdf"
# size = 204800
```

### `delete_file(file_path) -> None`

Removes a file from storage if it exists. Uses `os.path.exists` as a guard before calling `os.remove`. This is a synchronous function.

## Directory Structure

```
{UPLOAD_DIR}/
  knowledge_bases/
    {kb_id}/
      {uuid_hex}.pdf
      {uuid_hex}.txt
      {uuid_hex}.docx
```

The `subdirectory` parameter is caller-defined, allowing flexible organization. The knowledge base upload flow typically uses `knowledge_bases/{kb_id}` as the subdirectory.

## Design Notes

- **UUID filenames** prevent collisions and avoid issues with special characters in user-provided filenames.
- **Chunked reads** (8192 bytes) keep memory usage constant regardless of file size.
- **No cloud backends** -- the current implementation is local-only. The module boundary (`base.py`) suggests a pluggable storage interface could be added later (e.g., S3, GCS).
- The original filename is not preserved on disk; it is stored in the `Document.filename` column instead.

## Relationship to Document Model

After `save_upload` returns, the caller creates a `Document` row with:
- `file_path` set to the returned path
- `file_size` set to the returned size
- `filename` set to the original upload filename
- `status` set to `"pending"` for async processing
