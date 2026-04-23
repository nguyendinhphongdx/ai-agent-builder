---
id: flows-chat-attachments-plan
title: Chat Attachments — Plan
domain: flows
tags: [chat, attachments, upload, multimodal, vision, plan]
related: [api-uploads, flows-chat-with-agent, frontend-feature-chat]
summary: Users attach images + documents (PDF, DOC/DOCX, XLS/XLSX, PPT/PPTX) to chat messages. Backend ingests & extracts text; images flow through to multimodal LLMs. Send button stays disabled while files are still processing.
status: draft
---

# Chat Attachments — Plan

> **Core UX rule.** "Send" button is **disabled** until every attached file has
> finished uploading AND extracting. This eliminates the class of bugs where the
> LLM sees `[File: invoice.pdf]` with no text because extraction wasn't done yet.

## 1. Scope

### Supported file types
| Category | Extensions | Path |
|---|---|---|
| Images | `jpg`, `jpeg`, `png`, `webp`, `gif` | passed as vision content |
| PDF | `pdf` | text extracted, appended as context |
| Word | `doc`, `docx` | text extracted |
| Excel | `xls`, `xlsx` | text extracted (sheet → markdown-ish table) |
| PowerPoint | `ppt`, `pptx` | text extracted (slide-by-slide) |
| Plain | `txt`, `md`, `csv` | content read directly |

### Out of scope (Phase 2+)
- Audio / video
- Screenshot capture button
- Image editing / annotation
- RAG over uploaded docs (that's the Knowledge Base feature)

## 2. User Stories

| # | Story |
|---|---|
| US-01 | Upload 1+ images and ask a question about them |
| US-02 | Upload a PDF/DOC/XLS/PPT and have the LLM answer based on its content |
| US-03 | Drag files onto the chat area to attach them |
| US-04 | Remove an attached file before sending |
| US-05 | See each file's status: uploading → processing → ready |
| US-06 | Send button disabled while ANY file is still processing |
| US-07 | See attached files rendered inside the message I sent |

## 3. Constraints (defaults — confirm before coding)

| Limit | Value |
|---|---|
| Max files per message | **10** |
| Max size per file | **10 MB** (matches existing `attachment` upload config) |
| PDF page truncation | first **50 pages** |
| Excel sheet truncation | first **5 sheets × 200 rows each** |
| PowerPoint slide cap | first **100 slides** |
| Polling interval (status) | **1 second** until `ready` or `failed` |

## 4. Data Model

### `files` (existing) — extend

Already has `storage_key`, `file_name`, `file_type`, `access`, `size`, `owner_id`, `entity_type`, `entity_id`, `metadata` (JSONB).

Add 3 columns via migration:
```sql
ALTER TABLE files
  ADD COLUMN processing_status VARCHAR(16) NOT NULL DEFAULT 'ready',
  ADD COLUMN extracted_text TEXT NULL,
  ADD COLUMN processing_error TEXT NULL;
```

`processing_status` enum:
- `ready` — image or non-doc type (no extraction needed)
- `processing` — doc extraction in flight
- `failed` — extraction raised; stored in `processing_error`

## 5. API Contracts

### 5.1 POST `/api/upload` — UPDATE existing

Behavior change for `type=attachment`:
- Image → saved, `processing_status='ready'`, return immediately
- Doc → saved, `processing_status='processing'`, spawn background task, return immediately

Response: existing `FileResponse` + 3 new fields.

### 5.2 GET `/api/upload/{file_id}` — UPDATE existing response

Add `processing_status`, `processing_error`. Client polls every 1s while `processing`.

### 5.3 POST `/api/conversations/{id}/chat` — UPDATE

Request shape:
```json
{
  "content": "Summarise this PDF",
  "attachment_ids": ["uuid1", "uuid2"]
}
```

Behavior:
1. Load attachments; verify ownership; verify `processing_status === 'ready'` for every ID
2. Persist user message with `attachments` meta (list of file IDs)
3. Build LLM content parts:
   - Image → `{"type": "image_url", "image_url": {"url": "data:..."}}` (base64 inline since storage is local)
   - Doc → insert `extracted_text` into system context or an extra user message block
4. Stream response as today (SSE)

### 5.4 `GET /api/conversations/{id}/messages` — UPDATE response

Each message can carry:
```json
{
  "attachments": [
    { "id": "uuid", "name": "invoice.pdf", "mime_type": "application/pdf", "url": "..." }
  ]
}
```

## 6. Backend Plan

### 6.1 Dependencies to add
```
python-pptx>=1.0        # PPTX parsing
openpyxl>=3.1           # XLSX parsing
pypdf                   # already installed
docx2txt                # already installed
```

For legacy `.doc` / `.xls` / `.ppt` (OLE-based): require LibreOffice or use `antiword`/`xlrd`. **Defer** — for Phase 1 accept only the `*.x` variants; return clear error for legacy formats.

### 6.2 Upload config — extend
```python
# apps/backend/app/uploads/config.py
"attachment": UploadTypeConfig(
    max_size=10 * 1024 * 1024,
    allowed_extensions=(
        # images
        "jpg", "jpeg", "png", "webp", "gif",
        # text/markup
        "txt", "md", "csv",
        # pdf
        "pdf",
        # office (new formats only Phase 1)
        "docx", "xlsx", "pptx",
    ),
    access="private",
    path="attachments",
    entity_types=("conversation", "message"),
),
```

### 6.3 Parsers module — new

`apps/backend/app/uploads/extractors.py`
```python
def extract_text(file_path: str, extension: str) -> str:
    """Route to the matching parser. Raises on failure."""
    match extension:
        case "pdf":     return extract_pdf(file_path)
        case "docx":    return extract_docx(file_path)
        case "xlsx":    return extract_xlsx(file_path)
        case "pptx":    return extract_pptx(file_path)
        case "txt"|"md"|"csv": return open(file_path).read()
```

Each parser enforces its truncation cap.

### 6.4 Background processing
FastAPI `BackgroundTasks` on the upload endpoint:
```python
if requires_extraction(file_type):
    db_file.processing_status = "processing"
    background.add_task(run_extraction, db_file.id)
```
`run_extraction` opens a new DB session, extracts, updates row (`ready` or `failed`).

### 6.5 Chat integration
Inside `execute_agent_stream`:
```python
if attachment_ids:
    attachments = await load_attachments(db, attachment_ids, user_id)
    blocks = []
    for a in attachments:
        if a.is_image:
            blocks.append(image_content_part(a))
        elif a.extracted_text:
            blocks.append(text_block(f"[Attached: {a.name}]\n{a.extracted_text}"))
    messages[-1].content = blocks_plus_user_text(blocks, user_text)
```

LLM providers that support vision today:
- OpenAI: gpt-4o, gpt-4o-mini (image_url)
- Anthropic: claude-3-5-sonnet, haiku 4.5 (image content blocks)
- Google Gemini: gemini-2.x (inline_data base64)
- Ollama: depends on model — skip vision for now

If the configured model is **not** multimodal and the message has image attachments → surface an error in the stream: `"This model doesn't support images — pick a multimodal model or remove the image"`.

## 7. Frontend Plan

### 7.1 `attachmentService.ts` — new
```ts
upload(file: File): Promise<Attachment>
getStatus(fileId: string): Promise<{ processing_status, processing_error? }>
getUrl(fileId: string): Promise<string>  // signed URL for preview
```

### 7.2 `useAttachments` hook — new
State per attachment:
```ts
type Attachment = {
  id: string;               // local id (optimistic)
  serverId?: string;        // file id from backend
  file: File;               // original File
  status: "uploading" | "processing" | "ready" | "failed";
  error?: string;
  previewUrl?: string;      // object URL for image preview
};
```

API:
```ts
{
  attachments: Attachment[],
  isBusy: boolean,          // true if ANY is uploading/processing — blocks Send
  add(files: File[]): void, // uploads + starts polling
  remove(id: string): void, // aborts upload / deletes server-side if uploaded
  clear(): void,
  readyIds(): string[],     // server IDs to pass to chat
}
```

Internals:
- On `add`, create local rows with `status: "uploading"` + object URL preview
- Upload → receive serverId + initial status
- If `processing`, poll `/upload/{serverId}` every 1s
- On `ready`: mark; on `failed`: show error chip

### 7.3 `ChatInput` — redesign
Layout:
```
┌──────────────────────────────────────────┐
│ [thumbnail] [thumbnail] [thumbnail] …    │ ← attachments strip (if any)
│──────────────────────────────────────────│
│ 📎  [   textarea   ]            [Send]  │ ← input row
└──────────────────────────────────────────┘
 drop zone: entire card accepts files
```

Behaviour:
- `📎` paperclip → `<input type="file" multiple accept="image/*,.pdf,.docx,.xlsx,.pptx,.txt,.md,.csv">`
- Drag-drop: `onDragOver` shows tinted overlay; `onDrop` calls `add(files)`
- Each thumbnail:
  - Image → `<img src={previewUrl} />`
  - Doc → colored icon + short filename
  - Overlay: spinner while `uploading`/`processing`, red X if `failed`, × remove button on hover
- Send button disabled when:
  ```ts
  disabled = (!text && ready.length === 0) || hookIsBusy || streamInFlight
  ```
- Props change: `onSend(content: string, attachmentIds: string[])`

### 7.4 `useChatStream.sendMessage` — update
```ts
sendMessage(content: string, attachmentIds?: string[])
// POST body now: { content, attachment_ids: attachmentIds ?? [] }
```

### 7.5 `MessageBubble` — render attachments
- On `user` messages with `attachments`: show thumbnail grid above the text
- On `assistant` messages: no-op (provider output is pure text/tokens)

## 8. Security

- Ownership check on every attachment access (`owner_id == current_user.id`)
- Chat endpoint rejects attachment IDs the current user doesn't own
- Serve private files via time-limited signed URL (existing storage abstraction handles this)
- Extracted text stored in DB — not exposed publicly; only embedded in prompts

## 9. Error surfaces

| Failure | FE behaviour |
|---|---|
| Upload 4xx (size / MIME) | Red chip + `toast.error(detail)` |
| Extraction failed | Red chip "Couldn't read filename" + remove option |
| Model doesn't support images | Backend emits SSE error; FE toasts; user removes image or switches model |
| Network drop mid-upload | Chip shows `failed`, user removes or re-adds |

## 10. Decision Points

| # | Question | Default | Confirm? |
|---|---|---|---|
| D1 | Accept legacy `.doc/.xls/.ppt`? | **No** — Phase 1 rejects with clear error. User re-saves as `.docx`/`.xlsx`/`.pptx` | ☐ |
| D2 | Max files per message | **10** | ☐ |
| D3 | Max size per file | **10 MB** | ☐ |
| D4 | PDF page cap | **50** | ☐ |
| D5 | Storage backend | Local `uploads/attachments/` Phase 1; S3 later | ☐ |
| D6 | Progress UX | Poll every 1s | ☐ |
| D7 | Image delivery to LLM | Base64 inline (storage is local) | ☐ |
| D8 | Block sending if **any** attachment failed? | **Yes** — user must remove failed ones first | ☐ |

## 11. Implementation Phases

### Phase 1 — BE foundation (0.5 day)
- Alembic migration: add 3 cols to `files`
- Extend upload config
- Install parsers; write `extractors.py`
- Upload endpoint: trigger background extraction

### Phase 2 — BE chat integration (0.5 day)
- `ChatRequest.attachment_ids`
- Load + validate attachments in SSE handler
- Build vision / text blocks per provider
- Multimodal guard error when model can't do vision

### Phase 3 — FE hook + service (0.5 day)
- `attachmentService`
- `useAttachments` hook with polling

### Phase 4 — FE UI (0.5 day)
- Redesign `ChatInput` with paperclip + thumbnails + drag-drop
- Update `useChatStream.sendMessage` signature
- `MessageBubble` renders attachments

### Phase 5 — Polish (0.5 day)
- Toast errors, loading states, empty states
- Manual test matrix: each file type + multi-file + failure cases

Total: ~**2.5 days**.

## 12. Out-of-scope / future

- RAG over uploaded docs — distinct feature (Knowledge Base)
- Rename / reorder attachments before send
- Client-side image compression before upload
- Inline markdown preview of PDF text
- `.doc/.xls/.ppt` (requires LibreOffice headless conversion)
- Screenshot capture tool
- Paste-from-clipboard image support

---

_Confirm D1–D8, then Phase 1 starts._
