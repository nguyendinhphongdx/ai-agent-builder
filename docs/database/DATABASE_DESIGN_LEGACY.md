# Database Design

## Overview
- **Engine**: PostgreSQL 16+
- **Extensions**: `pgcrypto` (UUID), `vector` (pgvector cho embeddings)
- **ORM**: SQLAlchemy 2.0 (async, mapped_column style)
- **Migrations**: Alembic
- **Naming convention**: snake_case, plural table names

---

## ER Diagram (Simplified)

```
users
  ├── agents
  │     ├── agent_tools ──────── tools
  │     ├── agent_knowledge_bases ── knowledge_bases
  │     │                               └── documents
  │     │                                     └── document_chunks (vector)
  │     ├── conversations
  │     │     └── messages
  │     └── workflows
  │           ├── workflow_nodes
  │           └── workflow_edges
  └── tools
  └── knowledge_bases
```

---

## Tables

### 1. users

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default gen_random_uuid() | |
| email | VARCHAR(255) | UNIQUE, NOT NULL | Login email |
| hashed_password | VARCHAR(255) | NOT NULL | bcrypt hash |
| full_name | VARCHAR(255) | | Display name |
| avatar_url | VARCHAR(512) | | Profile image URL |
| is_active | BOOLEAN | DEFAULT TRUE | Soft disable account |
| last_login_at | TIMESTAMPTZ | | Last login timestamp |
| created_at | TIMESTAMPTZ | DEFAULT now() | |
| updated_at | TIMESTAMPTZ | DEFAULT now() | Auto-update on change |

**Indexes**: `UNIQUE(email)`

---

### 2. agents

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| user_id | UUID | FK -> users.id ON DELETE CASCADE, NOT NULL | Owner |
| name | VARCHAR(255) | NOT NULL | Agent display name |
| description | TEXT | | Short description |
| avatar_url | VARCHAR(512) | | Agent avatar |
| system_prompt | TEXT | NOT NULL | System instruction cho LLM |
| llm_provider | VARCHAR(50) | NOT NULL, DEFAULT 'openai' | 'openai', 'anthropic', 'ollama' |
| llm_model | VARCHAR(100) | NOT NULL, DEFAULT 'gpt-4o' | Model ID |
| llm_config | JSONB | DEFAULT '{}' | Xem chi tiết bên dưới |
| welcome_message | TEXT | | Tin nhắn chào khi bắt đầu conversation |
| max_turns | INT | DEFAULT 50 | Giới hạn turns per conversation |
| is_published | BOOLEAN | DEFAULT FALSE | Cho phép share public |
| status | VARCHAR(20) | DEFAULT 'draft' | 'draft', 'active', 'archived' |
| created_at | TIMESTAMPTZ | DEFAULT now() | |
| updated_at | TIMESTAMPTZ | DEFAULT now() | |

**`llm_config` JSONB structure:**
```json
{
  "temperature": 0.7,
  "max_tokens": 4096,
  "top_p": 1.0,
  "frequency_penalty": 0.0,
  "presence_penalty": 0.0,
  "stop_sequences": [],
  "response_format": null
}
```

**Indexes**: `INDEX(user_id)`, `INDEX(status)`

---

### 3. tools

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| user_id | UUID | FK -> users.id ON DELETE CASCADE, NOT NULL | Owner |
| name | VARCHAR(255) | NOT NULL | Tool name (LLM sees this) |
| description | TEXT | NOT NULL | Tool description (LLM dùng để quyết định khi nào gọi) |
| tool_type | VARCHAR(50) | NOT NULL | Xem enum bên dưới |
| config | JSONB | NOT NULL | Config khác nhau tùy tool_type |
| input_schema | JSONB | NOT NULL | JSON Schema mô tả parameters |
| output_schema | JSONB | | JSON Schema mô tả output (optional) |
| is_active | BOOLEAN | DEFAULT TRUE | Enable/disable tool |
| timeout_seconds | INT | DEFAULT 30 | Execution timeout |
| created_at | TIMESTAMPTZ | DEFAULT now() | |
| updated_at | TIMESTAMPTZ | DEFAULT now() | |

**`tool_type` enum values:**

| tool_type | Description |
|-----------|-------------|
| `http_request` | Gọi external API |
| `code_exec` | Execute Python/JS code snippet |
| `db_query` | Query database (read-only) |
| `web_scrape` | Scrape web page content |
| `custom_function` | User-defined Python function |

**`config` JSONB per tool_type:**

```json
// tool_type = "http_request"
{
  "method": "GET",
  "url": "https://api.example.com/users/{user_id}",
  "headers": {
    "Authorization": "Bearer {{secret.api_key}}",
    "Content-Type": "application/json"
  },
  "body_template": "{\"query\": \"{search_term}\"}",
  "response_mapping": "$.data.results"
}

// tool_type = "code_exec"
{
  "language": "python",
  "code_template": "def execute(input_data):\n    return input_data['x'] * 2",
  "sandbox": true,
  "max_memory_mb": 128
}

// tool_type = "db_query"
{
  "connection_id": "uuid-of-saved-connection",
  "query_template": "SELECT * FROM products WHERE name ILIKE '%{search}%' LIMIT 10",
  "read_only": true,
  "max_rows": 100
}

// tool_type = "web_scrape"
{
  "url_template": "https://example.com/search?q={query}",
  "selector": "div.content",
  "output_format": "text",
  "max_length": 5000
}

// tool_type = "custom_function"
{
  "function_code": "async def execute(**kwargs):\n    return {'result': kwargs['a'] + kwargs['b']}",
  "dependencies": ["requests", "beautifulsoup4"]
}
```

**`input_schema` example:**
```json
{
  "type": "object",
  "properties": {
    "user_id": {
      "type": "string",
      "description": "The user ID to look up"
    },
    "include_details": {
      "type": "boolean",
      "description": "Whether to include full details",
      "default": false
    }
  },
  "required": ["user_id"]
}
```

**Indexes**: `INDEX(user_id)`, `INDEX(tool_type)`

---

### 4. agent_tools (junction)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| agent_id | UUID | FK -> agents.id ON DELETE CASCADE | |
| tool_id | UUID | FK -> tools.id ON DELETE CASCADE | |
| priority | INT | DEFAULT 0 | Thứ tự ưu tiên khi hiển thị |
| added_at | TIMESTAMPTZ | DEFAULT now() | |

**PK**: `(agent_id, tool_id)`

---

### 5. knowledge_bases

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| user_id | UUID | FK -> users.id ON DELETE CASCADE, NOT NULL | Owner |
| name | VARCHAR(255) | NOT NULL | KB display name |
| description | TEXT | | Mô tả nội dung KB (LLM cũng thấy) |
| embedding_provider | VARCHAR(50) | DEFAULT 'openai' | 'openai', 'cohere', 'local' |
| embedding_model | VARCHAR(100) | DEFAULT 'text-embedding-3-small' | Model ID |
| embedding_dimensions | INT | DEFAULT 1536 | Vector dimension |
| chunk_size | INT | DEFAULT 1000 | Characters per chunk |
| chunk_overlap | INT | DEFAULT 200 | Overlap giữa các chunks |
| chunk_strategy | VARCHAR(50) | DEFAULT 'recursive' | 'recursive', 'semantic', 'fixed' |
| retrieval_top_k | INT | DEFAULT 5 | Default số chunks trả về |
| retrieval_score_threshold | FLOAT | DEFAULT 0.7 | Minimum similarity score |
| total_documents | INT | DEFAULT 0 | Denormalized count |
| total_chunks | INT | DEFAULT 0 | Denormalized count |
| status | VARCHAR(20) | DEFAULT 'active' | 'active', 'indexing', 'error' |
| created_at | TIMESTAMPTZ | DEFAULT now() | |
| updated_at | TIMESTAMPTZ | DEFAULT now() | |

**Indexes**: `INDEX(user_id)`

---

### 6. agent_knowledge_bases (junction)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| agent_id | UUID | FK -> agents.id ON DELETE CASCADE | |
| knowledge_base_id | UUID | FK -> knowledge_bases.id ON DELETE CASCADE | |
| added_at | TIMESTAMPTZ | DEFAULT now() | |

**PK**: `(agent_id, knowledge_base_id)`

---

### 7. documents

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| knowledge_base_id | UUID | FK -> knowledge_bases.id ON DELETE CASCADE, NOT NULL | |
| filename | VARCHAR(512) | NOT NULL | Original filename |
| file_path | VARCHAR(1024) | NOT NULL | Storage path (local or S3 key) |
| file_type | VARCHAR(20) | NOT NULL | 'pdf', 'txt', 'md', 'docx', 'csv', 'html' |
| file_size | BIGINT | | Size in bytes |
| mime_type | VARCHAR(100) | | MIME type |
| content_hash | VARCHAR(64) | | SHA-256 hash (detect duplicates) |
| chunk_count | INT | DEFAULT 0 | Number of chunks generated |
| token_count | INT | | Estimated total tokens |
| status | VARCHAR(20) | DEFAULT 'pending' | Xem enum bên dưới |
| error_message | TEXT | | Error details if failed |
| metadata | JSONB | DEFAULT '{}' | Extra info (page count, author...) |
| processing_started_at | TIMESTAMPTZ | | |
| processing_completed_at | TIMESTAMPTZ | | |
| created_at | TIMESTAMPTZ | DEFAULT now() | |

**`status` values:**

| Status | Description |
|--------|-------------|
| `pending` | Uploaded, chờ xử lý |
| `processing` | Đang parse + chunk + embed |
| `ready` | Xong, sẵn sàng query |
| `failed` | Lỗi trong quá trình xử lý |
| `deleting` | Đang xóa chunks |

**Indexes**: `INDEX(knowledge_base_id)`, `INDEX(status)`, `UNIQUE(knowledge_base_id, content_hash)`

---

### 8. document_chunks

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| document_id | UUID | FK -> documents.id ON DELETE CASCADE, NOT NULL | |
| knowledge_base_id | UUID | FK -> knowledge_bases.id ON DELETE CASCADE, NOT NULL | Denormalized for fast query |
| chunk_index | INT | NOT NULL | Thứ tự chunk trong document |
| content | TEXT | NOT NULL | Nội dung text của chunk |
| token_count | INT | | Estimated tokens in chunk |
| embedding | vector(1536) | | pgvector embedding |
| metadata | JSONB | DEFAULT '{}' | Xem chi tiết bên dưới |
| created_at | TIMESTAMPTZ | DEFAULT now() | |

**`metadata` JSONB structure:**
```json
{
  "source": "report.pdf",
  "page": 5,
  "heading": "Chapter 3: Results",
  "start_char": 12500,
  "end_char": 13500
}
```

**Indexes**:
- `INDEX(document_id)`
- `INDEX(knowledge_base_id)`
- `IVFFLAT(embedding vector_cosine_ops) WITH (lists = 100)` -- vector similarity search
- `INDEX(knowledge_base_id, chunk_index)` -- ordered retrieval

---

### 9. workflows

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| user_id | UUID | FK -> users.id ON DELETE CASCADE, NOT NULL | Owner |
| agent_id | UUID | FK -> agents.id ON DELETE SET NULL | Gắn workflow vào agent (optional) |
| name | VARCHAR(255) | NOT NULL | Workflow display name |
| description | TEXT | | |
| version | INT | DEFAULT 1 | Auto-increment on save |
| is_active | BOOLEAN | DEFAULT FALSE | Enable cho execution |
| viewport | JSONB | DEFAULT '{}' | Canvas zoom/pan state |
| created_at | TIMESTAMPTZ | DEFAULT now() | |
| updated_at | TIMESTAMPTZ | DEFAULT now() | |

**`viewport` JSONB:**
```json
{
  "x": 0,
  "y": 0,
  "zoom": 1.0
}
```

**Indexes**: `INDEX(user_id)`, `INDEX(agent_id)`

---

### 10. workflow_nodes

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| workflow_id | UUID | FK -> workflows.id ON DELETE CASCADE, NOT NULL | |
| node_type | VARCHAR(50) | NOT NULL | Xem enum bên dưới |
| label | VARCHAR(255) | | Display name on canvas |
| config | JSONB | NOT NULL, DEFAULT '{}' | Config tùy node_type |
| position_x | FLOAT | DEFAULT 0 | Canvas X position |
| position_y | FLOAT | DEFAULT 0 | Canvas Y position |
| width | FLOAT | | Custom node width |
| height | FLOAT | | Custom node height |
| created_at | TIMESTAMPTZ | DEFAULT now() | |

**`node_type` enum:**

| node_type | Description |
|-----------|-------------|
| `start` | Entry point |
| `end` | Exit point |
| `llm` | LLM call node |
| `tool` | Tool execution node |
| `condition` | Conditional branching |
| `human_input` | Wait for user input |
| `code` | Inline code execution |
| `subgraph` | Nested workflow |
| `knowledge_retrieval` | RAG query node |
| `merge` | Merge multiple branches |

**`config` JSONB per node_type:**

```json
// node_type = "start"
{
  "input_variables": ["user_input"]
}

// node_type = "end"
{
  "output_variable": "final_response"
}

// node_type = "llm"
{
  "llm_provider": "openai",
  "llm_model": "gpt-4o",
  "llm_config": {"temperature": 0.7},
  "system_prompt": "You are a helpful classifier.",
  "user_prompt_template": "Classify this: {user_input}",
  "output_variable": "classification",
  "enable_tools": false,
  "tool_ids": []
}

// node_type = "tool"
{
  "tool_id": "uuid-of-tool",
  "input_mapping": {
    "query": "{user_input}"
  },
  "output_variable": "tool_result"
}

// node_type = "condition"
{
  "conditions": [
    {
      "label": "Is billing",
      "expression": "classification == 'billing'",
      "target_handle": "billing"
    },
    {
      "label": "Is technical",
      "expression": "classification == 'technical'",
      "target_handle": "technical"
    }
  ],
  "default_handle": "other"
}

// node_type = "human_input"
{
  "prompt_message": "Please provide more details:",
  "timeout_seconds": 300,
  "output_variable": "human_response"
}

// node_type = "code"
{
  "language": "python",
  "code": "result = len(user_input.split())",
  "input_variables": ["user_input"],
  "output_variable": "word_count"
}

// node_type = "subgraph"
{
  "workflow_id": "uuid-of-nested-workflow",
  "input_mapping": {"user_input": "{current_context}"},
  "output_variable": "sub_result"
}

// node_type = "knowledge_retrieval"
{
  "knowledge_base_ids": ["uuid-1", "uuid-2"],
  "query_template": "{user_input}",
  "top_k": 5,
  "score_threshold": 0.7,
  "output_variable": "retrieved_context"
}

// node_type = "merge"
{
  "strategy": "concatenate",
  "input_variables": ["branch_a_result", "branch_b_result"],
  "output_variable": "merged_result",
  "separator": "\n\n"
}
```

**Indexes**: `INDEX(workflow_id)`

---

### 11. workflow_edges

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| workflow_id | UUID | FK -> workflows.id ON DELETE CASCADE, NOT NULL | |
| source_node_id | UUID | FK -> workflow_nodes.id ON DELETE CASCADE, NOT NULL | |
| target_node_id | UUID | FK -> workflow_nodes.id ON DELETE CASCADE, NOT NULL | |
| source_handle | VARCHAR(100) | | Output handle ID (for condition nodes) |
| target_handle | VARCHAR(100) | | Input handle ID |
| label | VARCHAR(255) | | Edge label on canvas |
| style | JSONB | DEFAULT '{}' | Visual style (color, animated...) |
| created_at | TIMESTAMPTZ | DEFAULT now() | |

**`style` JSONB:**
```json
{
  "stroke_color": "#10b981",
  "stroke_width": 2,
  "animated": true
}
```

**Indexes**: `INDEX(workflow_id)`, `INDEX(source_node_id)`, `INDEX(target_node_id)`

---

### 12. workflow_runs

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| workflow_id | UUID | FK -> workflows.id ON DELETE CASCADE, NOT NULL | |
| user_id | UUID | FK -> users.id ON DELETE CASCADE, NOT NULL | Who triggered |
| conversation_id | UUID | FK -> conversations.id ON DELETE SET NULL | Associated chat (optional) |
| status | VARCHAR(20) | DEFAULT 'running' | 'running', 'completed', 'failed', 'cancelled' |
| input_data | JSONB | NOT NULL | Initial input |
| output_data | JSONB | | Final output |
| error_message | TEXT | | Error if failed |
| node_executions | JSONB | DEFAULT '[]' | Xem chi tiết bên dưới |
| total_tokens | INT | DEFAULT 0 | Sum of all LLM calls |
| total_cost | DECIMAL(10,6) | DEFAULT 0 | Estimated cost |
| started_at | TIMESTAMPTZ | DEFAULT now() | |
| completed_at | TIMESTAMPTZ | | |

**`node_executions` JSONB** (execution trace):
```json
[
  {
    "node_id": "llm_1",
    "node_type": "llm",
    "status": "completed",
    "input": {"user_input": "I need help with billing"},
    "output": {"classification": "billing"},
    "tokens": {"prompt": 150, "completion": 5},
    "latency_ms": 820,
    "started_at": "2026-04-09T10:00:01Z",
    "completed_at": "2026-04-09T10:00:02Z"
  },
  {
    "node_id": "tool_1",
    "node_type": "tool",
    "status": "completed",
    "input": {"query": "billing help"},
    "output": {"result": "..."},
    "latency_ms": 350,
    "started_at": "2026-04-09T10:00:02Z",
    "completed_at": "2026-04-09T10:00:02.350Z"
  }
]
```

**Indexes**: `INDEX(workflow_id)`, `INDEX(user_id)`, `INDEX(status)`

---

### 13. conversations

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| user_id | UUID | FK -> users.id ON DELETE CASCADE, NOT NULL | |
| agent_id | UUID | FK -> agents.id ON DELETE CASCADE, NOT NULL | |
| title | VARCHAR(255) | | Auto-generated hoặc user set |
| is_pinned | BOOLEAN | DEFAULT FALSE | Pin conversation |
| is_archived | BOOLEAN | DEFAULT FALSE | Soft archive |
| summary | TEXT | | Auto-generated conversation summary |
| total_messages | INT | DEFAULT 0 | Denormalized count |
| total_tokens | INT | DEFAULT 0 | Sum of all message tokens |
| metadata | JSONB | DEFAULT '{}' | Extra context |
| last_message_at | TIMESTAMPTZ | | Timestamp of latest message |
| created_at | TIMESTAMPTZ | DEFAULT now() | |
| updated_at | TIMESTAMPTZ | DEFAULT now() | |

**Indexes**: `INDEX(user_id, last_message_at DESC)`, `INDEX(agent_id)`, `INDEX(is_archived)`

---

### 14. messages

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| conversation_id | UUID | FK -> conversations.id ON DELETE CASCADE, NOT NULL | |
| parent_message_id | UUID | FK -> messages.id ON DELETE SET NULL | For branching conversations |
| role | VARCHAR(20) | NOT NULL | 'user', 'assistant', 'system', 'tool' |
| content | TEXT | NOT NULL | Message content |
| content_type | VARCHAR(20) | DEFAULT 'text' | 'text', 'markdown', 'image', 'file' |
| tool_calls | JSONB | | Xem chi tiết bên dưới |
| tool_call_id | VARCHAR(255) | | ID khi message là tool response |
| tool_name | VARCHAR(255) | | Tool name khi role = 'tool' |
| attachments | JSONB | DEFAULT '[]' | File attachments |
| token_usage | JSONB | | Token consumption |
| latency_ms | INT | | Response time |
| llm_model | VARCHAR(100) | | Which model generated this |
| feedback | VARCHAR(10) | | 'like', 'dislike' (user feedback) |
| created_at | TIMESTAMPTZ | DEFAULT now() | |

**`tool_calls` JSONB** (when assistant decides to call tools):
```json
[
  {
    "id": "call_abc123",
    "type": "function",
    "function": {
      "name": "search_knowledge",
      "arguments": "{\"query\": \"billing policy\"}"
    }
  }
]
```

**`token_usage` JSONB:**
```json
{
  "prompt_tokens": 1250,
  "completion_tokens": 340,
  "total_tokens": 1590
}
```

**`attachments` JSONB:**
```json
[
  {
    "filename": "screenshot.png",
    "file_path": "uploads/conv/uuid/screenshot.png",
    "file_type": "image/png",
    "file_size": 245000
  }
]
```

**Indexes**: `INDEX(conversation_id, created_at)`, `INDEX(role)`, `INDEX(parent_message_id)`

---

### 15. api_keys (for LLM providers)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| user_id | UUID | FK -> users.id ON DELETE CASCADE, NOT NULL | |
| provider | VARCHAR(50) | NOT NULL | 'openai', 'anthropic', 'cohere', 'ollama' |
| name | VARCHAR(255) | NOT NULL | User-friendly label |
| encrypted_key | TEXT | NOT NULL | AES-256 encrypted API key |
| is_default | BOOLEAN | DEFAULT FALSE | Default key for this provider |
| last_used_at | TIMESTAMPTZ | | |
| created_at | TIMESTAMPTZ | DEFAULT now() | |

**Indexes**: `INDEX(user_id, provider)`, `UNIQUE(user_id, provider, name)`

---

### 16. db_connections (for db_query tools)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| user_id | UUID | FK -> users.id ON DELETE CASCADE, NOT NULL | |
| name | VARCHAR(255) | NOT NULL | Connection label |
| db_type | VARCHAR(20) | NOT NULL | 'postgresql', 'mysql', 'sqlite', 'mssql' |
| host | VARCHAR(255) | NOT NULL | |
| port | INT | NOT NULL | |
| database_name | VARCHAR(255) | NOT NULL | |
| username | VARCHAR(255) | NOT NULL | |
| encrypted_password | TEXT | NOT NULL | AES-256 encrypted |
| ssl_enabled | BOOLEAN | DEFAULT FALSE | |
| max_query_rows | INT | DEFAULT 100 | Safety limit |
| query_timeout_seconds | INT | DEFAULT 10 | |
| is_read_only | BOOLEAN | DEFAULT TRUE | Force read-only connection |
| created_at | TIMESTAMPTZ | DEFAULT now() | |
| updated_at | TIMESTAMPTZ | DEFAULT now() | |

**Indexes**: `INDEX(user_id)`

---

## Common Patterns

### TimestampMixin (SQLAlchemy)
```python
class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, server_default=func.now(), onupdate=func.now()
    )
```

### UUID Primary Key
All tables use UUID v4 as primary key, generated server-side via `gen_random_uuid()`.

### Soft Delete vs Hard Delete
- **Hard delete**: tools, documents, document_chunks, workflow_nodes, workflow_edges (CASCADE from parent)
- **Soft delete via status/flag**: users (`is_active`), agents (`status: archived`), conversations (`is_archived`)

### JSONB Validation
JSONB fields are validated at application layer using Pydantic discriminated unions per type. Database stores raw JSON.

### Denormalized Counts
`knowledge_bases.total_documents`, `knowledge_bases.total_chunks`, `conversations.total_messages` are denormalized for fast reads. Updated via application logic after inserts/deletes.

---

## Migration Order

```
1. extensions (pgcrypto, vector)
2. users
3. agents
4. tools
5. agent_tools
6. knowledge_bases
7. agent_knowledge_bases
8. documents
9. document_chunks
10. workflows
11. workflow_nodes
12. workflow_edges
13. workflow_runs
14. conversations
15. messages
16. api_keys
17. db_connections
```
