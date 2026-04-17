# Kiến trúc hệ thống - AI Agent Builder

> Tài liệu kiến trúc chi tiết cho toàn bộ hệ thống. Mọi thay đổi kiến trúc cần được cập nhật vào đây **trước khi** triển khai code.

## Mục lục

1. [Tổng quan hệ thống](#1-tổng-quan-hệ-thống)
2. [Kiến trúc Backend](#2-kiến-trúc-backend)
3. [Kiến trúc Frontend](#3-kiến-trúc-frontend)
4. [Kiến trúc Database](#4-kiến-trúc-database)
5. [Luồng dữ liệu](#5-luồng-dữ-liệu)
6. [Hệ thống xác thực](#6-hệ-thống-xác-thực)
7. [Agent Engine](#7-agent-engine)
8. [Tool Registry](#8-tool-registry)
9. [RAG Pipeline](#9-rag-pipeline)
10. [Workflow Engine](#10-workflow-engine)
11. [Multi-Agent](#11-multi-agent)
12. [LLM Provider Abstraction](#12-llm-provider-abstraction)
13. [WebSocket Streaming](#13-websocket-streaming)
14. [Triển khai & Docker](#14-triển-khai--docker)
15. [Quyết định thiết kế](#15-quyết-định-thiết-kế)

---

## 1. Tổng quan hệ thống

### Sơ đồ kiến trúc

```
┌─────────────┐     REST / WS      ┌──────────────────┐
│   Next.js   │ ◄────────────────► │   FastAPI         │
│  Frontend   │   HTTP-only cookie │   Backend         │
│  (port 3000)│                    │   (port 8000)     │
└─────────────┘                    └────────┬──────────┘
                                            │
                               ┌────────────┼────────────┐
                               │            │            │
                               ▼            ▼            ▼
                        ┌──────────┐ ┌──────────┐ ┌──────────┐
                        │PostgreSQL│ │ LangGraph│ │   LLM    │
                        │+ pgvector│ │  Engine  │ │Providers │
                        │(port 5432│ │          │ │(OpenAI,  │
                        └──────────┘ └──────────┘ │Anthropic,│
                                                  │ Ollama)  │
                                                  └──────────┘
```

### Tech Stack

| Thành phần | Công nghệ | Phiên bản |
|-----------|-----------|-----------|
| Backend Framework | FastAPI (async) | >= 0.115 |
| Agent Engine | LangGraph + LangChain | >= 0.2 / >= 0.3 |
| ORM | SQLAlchemy 2.0 (async) | >= 2.0 |
| Database | PostgreSQL + pgvector | 16+ |
| Migration | Alembic | >= 1.14 |
| Frontend Framework | Next.js (App Router) | 16 |
| UI Library | shadcn/ui + TailwindCSS | 4 |
| State (client) | Zustand | 5 |
| State (server) | TanStack React Query | 5 |
| Workflow Editor | @xyflow/react (React Flow) | 12 |
| Auth | JWT (python-jose) + bcrypt | - |
| Container | Docker Compose | - |

---

## 2. Kiến trúc Backend

### Cấu trúc module

```
backend/app/
├── main.py                  # App factory, CORS, đăng ký routers, WebSocket
├── config.py                # Pydantic Settings (đọc từ .env)
│
├── db/                      # Tầng database
│   ├── base.py              # DeclarativeBase + UUIDMixin + TimestampMixin
│   └── session.py           # AsyncSession factory + get_db dependency
│
├── models/                  # SQLAlchemy ORM models (14 bảng)
│   ├── user.py              # Tài khoản người dùng
│   ├── agent.py             # AI agent + bảng trung gian (AgentTool, AgentKnowledgeBase)
│   ├── tool.py              # Định nghĩa tool tùy chỉnh
│   ├── knowledge_base.py    # Cấu hình RAG
│   ├── document.py          # Tài liệu đã upload
│   ├── document_chunk.py    # Chunk với pgvector embedding
│   ├── conversation.py      # Cuộc hội thoại
│   ├── message.py           # Tin nhắn
│   ├── workflow.py          # Workflow graph
│   ├── workflow_node.py     # Node trong workflow
│   ├── workflow_edge.py     # Cạnh nối
│   ├── workflow_run.py      # Lịch sử thực thi
│   └── api_key.py           # API key mã hóa
│
├── auth/                    # Module xác thực
│   ├── router.py            # Endpoints: register, login, refresh, logout, me
│   ├── service.py           # Hash password, tạo/giải mã JWT
│   ├── dependencies.py      # Dependency get_current_user (đọc cookie)
│   └── schemas.py           # RegisterRequest, LoginRequest, AuthResponse
│
├── agents/                  # Module quản lý agent
│   ├── router.py            # CRUD agent + gắn/gỡ tool/KB
│   ├── service.py           # Thao tác DB agent
│   ├── executor.py          # LangGraph ReAct agent + streaming events
│   └── schemas.py           # AgentCreate, AgentResponse, ToolBrief, ...
│
├── tools/                   # Module quản lý tool
│   ├── router.py            # CRUD tool + test endpoint
│   ├── service.py           # Thao tác DB tool
│   ├── registry.py          # ToolRegistry + 4 builders (HTTP, code, scrape, DB)
│   ├── schemas.py           # ToolCreate, ToolResponse
│   └── builtins/            # (Dự phòng cho tool có sẵn)
│
├── knowledge/               # Module RAG
│   ├── router.py            # CRUD KB, upload tài liệu, query
│   ├── service.py           # Thao tác DB knowledge base + document
│   ├── ingestion.py         # Parse file -> chunk -> embed -> lưu pgvector
│   ├── retriever.py         # Tìm kiếm ngữ nghĩa cosine similarity
│   └── schemas.py           # KBCreate, DocumentResponse, RetrievalQuery
│
├── workflows/               # Module workflow engine
│   ├── router.py            # CRUD workflow, execute, lịch sử runs
│   ├── service.py           # Thao tác DB workflow + save graph
│   ├── compiler.py          # JSON graph -> LangGraph StateGraph -> thực thi
│   ├── schemas.py           # WorkflowCreate, NodeConfig, ExecuteRequest
│   └── nodes/
│       └── executor.py      # 6 node executors (input, output, LLM, tool, condition, human_input)
│
├── conversations/           # Module chat
│   ├── router.py            # CRUD conversation + lấy tin nhắn
│   ├── service.py           # Thao tác DB conversation + message
│   ├── ws.py                # WebSocket handler với streaming LLM
│   └── schemas.py           # ConversationCreate, MessageResponse
│
├── multi_agent/             # Module đa agent
│   ├── router.py            # Endpoints: supervisor, peer, providers
│   ├── supervisor.py        # Supervisor pattern (1 điều phối + N workers)
│   ├── peer.py              # Peer collaboration (tuần tự + tổng hợp)
│   └── schemas.py           # SupervisorRequest, PeerRequest, MultiAgentResponse
│
├── llm/                     # Lớp trừu tượng LLM
│   └── provider.py          # build_llm() hỗ trợ OpenAI, Anthropic, Ollama
│
└── storage/                 # Lưu trữ file
    └── base.py              # save_upload(), delete_file()
```

### Pattern áp dụng

Mỗi module tuân theo kiến trúc 4 tầng:

```
Router (endpoints)  →  Service (business logic)  →  Models (ORM)
                              ↑
                        Schemas (validation)
```

- **Router**: Nhận request, gọi service, trả response. Không chứa logic nghiệp vụ.
- **Service**: Thao tác database, xử lý nghiệp vụ. Nhận `AsyncSession` qua dependency injection.
- **Schemas**: Pydantic models validate input/output. Dùng `from_attributes=True` để serialize từ ORM.
- **Models**: SQLAlchemy ORM. Kế thừa `UUIDMixin` (auto UUID PK) và `TimestampMixin` (created_at, updated_at).

### Dependency Injection

```python
# Session DB tự động commit/rollback
async def get_db() -> AsyncGenerator[AsyncSession, None]

# Xác thực user từ cookie
async def get_current_user(access_token: Cookie, db: Session) -> User
```

---

## 3. Kiến trúc Frontend

### Cấu trúc thư mục

```
frontend/src/
├── app/                          # Next.js App Router (tầng mỏng, chỉ routing)
│   ├── layout.tsx                # Root layout + providers
│   ├── page.tsx                  # Landing page
│   ├── (auth)/                   # Nhóm route xác thực
│   │   ├── login/page.tsx
│   │   └── register/page.tsx
│   └── (dashboard)/              # Nhóm route dashboard (cần auth)
│       ├── layout.tsx            # Sidebar + Header
│       ├── agents/               # Quản lý agent
│       ├── tools/                # Quản lý tool
│       ├── knowledge/            # Quản lý knowledge base
│       ├── workflows/            # Visual workflow editor
│       └── settings/             # Cài đặt
│
├── features/                     # Module theo tính năng (encapsulated)
│   ├── auth/                     # Xác thực
│   │   ├── views/                # LoginView, RegisterView
│   │   ├── components/           # LoginForm, RegisterForm
│   │   ├── hooks/                # useAuth (TanStack Query)
│   │   ├── services/             # authService (axios)
│   │   └── types/
│   ├── agents/                   # Quản lý agent
│   │   ├── views/                # AgentListView, AgentCreateView, AgentDetailView
│   │   ├── components/           # AgentCard, AgentForm, ToolsSelector
│   │   ├── hooks/                # useAgents
│   │   └── services/             # agentService
│   ├── tools/                    # Quản lý tool
│   ├── knowledge/                # Quản lý KB + upload + retrieval test
│   ├── workflows/                # Workflow editor
│   │   ├── components/
│   │   │   ├── Canvas.tsx        # React Flow wrapper
│   │   │   ├── NodePalette.tsx   # Bảng chọn loại node
│   │   │   ├── NodeInspector.tsx # Panel cấu hình node đang chọn
│   │   │   └── custom-nodes/     # LLMNode, ToolNode, ConditionNode, ...
│   │   └── stores/
│   │       └── workflowEditorStore.ts  # Zustand (nodes, edges, selected)
│   └── chat/                     # Chat interface
│       ├── components/           # ChatWindow, MessageBubble, ChatInput
│       ├── hooks/                # useChat (WebSocket), useConversations
│       └── stores/
│           └── chatStore.ts      # Zustand (messages, streaming state)
│
├── components/                   # Component dùng chung
│   ├── ui/                       # shadcn/ui (button, input, dialog, ...)
│   ├── layout/                   # Sidebar, Header, Breadcrumbs
│   ├── shared/                   # EmptyState, LoadingState, ErrorState
│   └── providers/                # QueryProvider, ThemeProvider, AuthProvider
│
├── lib/                          # Tiện ích dùng chung
│   ├── api/
│   │   ├── client.ts             # Axios instance + interceptor 401
│   │   └── endpoints.ts          # Hằng số URL API
│   └── ws/
│       └── client.ts             # WebSocket client factory
│
└── hooks/                        # Custom hooks dùng chung
    ├── useDebounce.ts
    └── useMediaQuery.ts
```

### Nguyên tắc quản lý state

| Loại state | Công cụ | Ví dụ |
|-----------|---------|-------|
| Server state (API data) | TanStack React Query | Danh sách agents, tools, conversations |
| Client UI state | Zustand | Streaming message, selected node, canvas viewport |
| Form state | React Hook Form + Zod | Tạo agent, tạo tool |
| URL state | Next.js App Router | Route params, search params |

**Quy tắc**: Không lưu server data vào Zustand. TanStack Query xử lý cache, refetch, optimistic updates.

### Axios Interceptor

```
Request bất kỳ → 401 Unauthorized
    → Tự động gọi POST /api/auth/refresh
    → Thành công → Retry request gốc
    → Thất bại → Redirect /login
```

---

## 4. Kiến trúc Database

### Sơ đồ quan hệ

```
users ─────────────────────────────────────────┐
  │                                            │
  ├── agents ─────────── conversations         │
  │     │                     │                │
  │     ├── agent_tools ◄──── messages         │
  │     │     │                                │
  │     │     └──► tools ◄────────────────── users
  │     │
  │     ├── agent_knowledge_bases
  │     │     │
  │     │     └──► knowledge_bases ◄───────── users
  │     │               │
  │     │               └── documents
  │     │                     │
  │     │                     └── document_chunks (pgvector)
  │     │
  │     └── workflows
  │           ├── workflow_nodes
  │           ├── workflow_edges
  │           └── workflow_runs
  │
  └── api_keys
```

### Chi tiết từng bảng

#### users

| Cột | Kiểu | Mô tả |
|-----|------|-------|
| id | UUID PK | Auto-generate UUID v4 |
| email | VARCHAR(255) UNIQUE | Địa chỉ email (indexed) |
| hashed_password | VARCHAR(255) | Mật khẩu bcrypt hash |
| full_name | VARCHAR(255) | Tên hiển thị |
| avatar_url | VARCHAR(512) | URL ảnh đại diện |
| is_active | BOOLEAN | Trạng thái tài khoản |
| last_login_at | TIMESTAMP(tz) | Thời gian đăng nhập cuối |
| created_at, updated_at | TIMESTAMP(tz) | Tự động cập nhật |

#### agents

| Cột | Kiểu | Mô tả |
|-----|------|-------|
| id | UUID PK | |
| user_id | UUID FK → users | Chủ sở hữu |
| name | VARCHAR(255) | Tên agent |
| description | TEXT | Mô tả |
| system_prompt | TEXT | Prompt hệ thống định nghĩa hành vi |
| llm_provider | VARCHAR(50) | "openai", "anthropic", "ollama" |
| llm_model | VARCHAR(100) | "gpt-4o", "claude-sonnet-4-20250514", ... |
| llm_config | JSONB | `{temperature, max_tokens, base_url, ...}` |
| welcome_message | TEXT | Tin nhắn chào khi bắt đầu hội thoại |
| max_turns | INTEGER | Giới hạn lượt trao đổi (mặc định 50) |
| is_published | BOOLEAN | Đã xuất bản hay chưa |
| status | VARCHAR(20) | "draft" hoặc "active" |

#### tools

| Cột | Kiểu | Mô tả |
|-----|------|-------|
| id | UUID PK | |
| user_id | UUID FK → users | Chủ sở hữu |
| name | VARCHAR(255) | Tên tool |
| description | TEXT | Mô tả cho LLM hiểu cách dùng |
| tool_type | VARCHAR(50) | "http_request", "code_exec", "web_scrape", "db_query" |
| config | JSONB | Cấu hình riêng theo tool_type |
| input_schema | JSONB | JSON Schema mô tả tham số đầu vào |
| output_schema | JSONB | JSON Schema mô tả kết quả |
| is_active | BOOLEAN | Bật/tắt tool |
| timeout_seconds | INTEGER | Thời gian chờ tối đa (mặc định 30) |

#### knowledge_bases

| Cột | Kiểu | Mô tả |
|-----|------|-------|
| id | UUID PK | |
| user_id | UUID FK → users | Chủ sở hữu |
| name | VARCHAR(255) | Tên knowledge base |
| embedding_provider | VARCHAR(50) | "openai" (mặc định) |
| embedding_model | VARCHAR(100) | "text-embedding-3-small" |
| embedding_dimensions | INTEGER | 1536 (số chiều vector) |
| chunk_size | INTEGER | 1000 (ký tự/chunk) |
| chunk_overlap | INTEGER | 200 (ký tự chồng lấp) |
| chunk_strategy | VARCHAR(50) | "recursive" |
| retrieval_top_k | INTEGER | 5 (số chunk trả về) |
| retrieval_score_threshold | FLOAT | 0.7 (ngưỡng điểm tối thiểu) |
| total_documents | INTEGER | Bộ đếm (denormalized) |
| total_chunks | INTEGER | Bộ đếm (denormalized) |

#### documents

| Cột | Kiểu | Mô tả |
|-----|------|-------|
| id | UUID PK | |
| knowledge_base_id | UUID FK | |
| filename | VARCHAR(512) | Tên file gốc |
| file_path | VARCHAR(1024) | Đường dẫn lưu trên server |
| file_type | VARCHAR(20) | "pdf", "txt", "md", "docx", "csv", "html" |
| file_size | BIGINT | Kích thước (bytes) |
| content_hash | VARCHAR(64) | SHA-256 phát hiện trùng lặp |
| chunk_count | INTEGER | Số chunk đã tạo |
| status | VARCHAR(20) | "pending" → "processing" → "completed" / "failed" |

#### document_chunks

| Cột | Kiểu | Mô tả |
|-----|------|-------|
| id | UUID PK | |
| document_id | UUID FK | |
| knowledge_base_id | UUID FK | Denormalized để query nhanh |
| chunk_index | INTEGER | Thứ tự chunk trong tài liệu |
| content | TEXT | Nội dung text |
| token_count | INTEGER | Số token |
| embedding | vector(1536) | pgvector embedding |
| metadata | JSONB | `{page, section, ...}` |

#### conversations

| Cột | Kiểu | Mô tả |
|-----|------|-------|
| id | UUID PK | |
| user_id | UUID FK → users | |
| agent_id | UUID FK → agents | |
| title | VARCHAR(255) | Tiêu đề |
| is_pinned | BOOLEAN | Ghim lên đầu |
| is_archived | BOOLEAN | Ẩn khỏi danh sách |
| summary | TEXT | Tóm tắt tự động |
| total_messages | INTEGER | Bộ đếm (denormalized) |
| total_tokens | INTEGER | Bộ đếm (denormalized) |
| last_message_at | TIMESTAMP(tz) | Sắp xếp theo mới nhất |

#### messages

| Cột | Kiểu | Mô tả |
|-----|------|-------|
| id | UUID PK | |
| conversation_id | UUID FK | |
| parent_message_id | UUID FK (self) | Hỗ trợ branching |
| role | VARCHAR(20) | "user", "assistant", "tool", "system" |
| content | TEXT | Nội dung tin nhắn |
| content_type | VARCHAR(20) | "text", "image", "file" |
| tool_calls | JSONB | Danh sách tool calls từ LLM |
| tool_call_id | VARCHAR(255) | ID tool call (cho role="tool") |
| tool_name | VARCHAR(255) | Tên tool đã thực thi |
| token_usage | JSONB | `{prompt_tokens, completion_tokens, total_tokens}` |
| latency_ms | INTEGER | Thời gian phản hồi LLM |
| feedback | VARCHAR(10) | "up" hoặc "down" |

#### workflows, workflow_nodes, workflow_edges, workflow_runs

| Bảng | Cột quan trọng |
|------|---------------|
| workflows | user_id, agent_id (tùy chọn), name, version, is_active, viewport (JSONB) |
| workflow_nodes | workflow_id, node_type, label, config (JSONB), position_x/y |
| workflow_edges | workflow_id, source_node_id, target_node_id, source_handle, target_handle |
| workflow_runs | workflow_id, user_id, status, input_data, output_data, node_executions (JSONB), total_tokens, total_cost |

#### api_keys

| Cột | Kiểu | Mô tả |
|-----|------|-------|
| id | UUID PK | |
| user_id | UUID FK | |
| provider | VARCHAR(50) | "openai", "anthropic", ... |
| name | VARCHAR(255) | Tên hiển thị do user đặt |
| encrypted_key | TEXT | API key đã mã hóa |
| is_default | BOOLEAN | Key mặc định cho provider |

### Index quan trọng

- `users.email` — UNIQUE, tìm kiếm khi đăng nhập
- `agents.user_id` — Lọc agent theo user
- `agents.status` — Lọc theo trạng thái
- `conversations.is_archived` — Lọc cuộc hội thoại đang hiện
- `documents.status` — Theo dõi trạng thái xử lý
- `document_chunks.embedding` — IVFFLAT index cho cosine similarity search

---

## 5. Luồng dữ liệu

### Chat với Agent

```
1. User gửi tin nhắn qua WebSocket
2. Backend lưu tin nhắn user vào DB
3. Tải agent config (system_prompt, llm_model, tools, KBs)
4. Xây dựng lịch sử hội thoại (50 tin nhắn gần nhất)
5. Tạo LangGraph ReAct agent với tools
6. Gọi LLM qua astream_events()
7. Stream từng token về client: {"type": "token", "content": "..."}
8. Nếu LLM gọi tool:
   a. Gửi {"type": "tool_start", "name": "...", "input": "..."}
   b. Thực thi tool
   c. Gửi {"type": "tool_end", "name": "...", "result": "..."}
   d. Trả kết quả tool cho LLM, tiếp tục generate
9. Lưu phản hồi assistant vào DB (kèm latency_ms, llm_model)
10. Gửi {"type": "done"}
```

### Upload tài liệu vào Knowledge Base

```
1. User upload file qua POST /api/knowledge-bases/{id}/documents
2. Lưu file vào storage (UUID naming)
3. Tạo Document record (status: "pending")
4. Parse file (PDF → pypdf, DOCX → docx2txt, ...)
5. Chia chunk (RecursiveCharacterTextSplitter: chunk_size=1000, overlap=200)
6. Embed từng chunk (OpenAI text-embedding-3-small → vector 1536 chiều)
7. Lưu chunks + embeddings vào document_chunks
8. Cập nhật Document.status → "completed"
9. Cập nhật bộ đếm KnowledgeBase (total_documents, total_chunks)
```

### Thực thi Workflow

```
1. User gọi POST /api/workflows/{id}/execute với input_data
2. Tạo WorkflowRun record (status: "running")
3. Compiler phân tích graph:
   a. Xây dựng adjacency list từ nodes + edges
   b. Tìm node bắt đầu (ưu tiên type="input")
4. Tạo LangGraph StateGraph:
   a. Đăng ký mỗi node là async function
   b. Đăng ký edges (thường hoặc conditional)
5. Compile và invoke graph với initial state
6. Mỗi node thực thi:
   - Input: pass-through dữ liệu
   - LLM: gọi LLM provider, trả về response
   - Tool: tìm tool trong DB, build, thực thi
   - Condition: eval biểu thức, routing true/false
   - Human Input: lấy từ input_data ban đầu
   - Output: đánh dấu kết quả cuối
7. Cập nhật WorkflowRun (status, output_data, node_executions, total_tokens)
```

### Multi-Agent: Supervisor

```
1. User gọi POST /api/multi-agent/supervisor
   Body: {message, agent_ids: [supervisor_id, worker1_id, worker2_id, ...]}
2. Tải tất cả agents từ DB
3. Build tools + LLM cho mỗi agent
4. Tạo LangGraph StateGraph:
   - Node "supervisor": LLM quyết định giao cho worker nào
   - Node cho mỗi worker: thực thi task
5. Vòng lặp:
   a. Supervisor nhận message → parse "ROUTE: <worker_name>"
   b. Worker thực thi → trả kết quả
   c. Supervisor đánh giá → tiếp tục hoặc "ROUTE: FINISH"
6. Trả về response + kết quả từng worker
```

### Multi-Agent: Peer Collaboration

```
1. User gọi POST /api/multi-agent/peer
   Body: {message, agent_ids: [a1, a2, a3], synthesis_prompt?}
2. Tải tất cả agents
3. Tạo pipeline tuần tự: Agent A → Agent B → Agent C
4. Mỗi agent nhận:
   - Agent đầu: user message gốc
   - Các agent sau: user message + output agent trước
5. Nếu có synthesis_prompt: thêm node tổng hợp cuối
6. Trả về response + output từng agent
```

---

## 6. Hệ thống xác thực

### Luồng xác thực

```
Đăng ký/Đăng nhập
    → Backend tạo access_token (30 phút) + refresh_token (7 ngày)
    → Gán vào HTTP-only cookie (secure, samesite=lax)
    → access_token: path="/" (gửi mọi request)
    → refresh_token: path="/api/auth/refresh" (chỉ gửi khi refresh)

Mỗi request
    → Middleware đọc access_token từ cookie
    → Giải mã JWT, kiểm tra type="access"
    → Tìm user trong DB, kiểm tra is_active
    → Trả về User object cho endpoint

Token hết hạn
    → Frontend nhận 401
    → Tự động gọi POST /api/auth/refresh
    → Backend đọc refresh_token cookie, tạo cặp token mới
    → Retry request gốc
    → Nếu refresh cũng hết hạn → redirect /login
```

### Bảo mật

- Mật khẩu: bcrypt hash (passlib)
- Token: JWT HS256 (python-jose)
- Cookie: `httponly=True, secure=True, samesite=lax`
- Refresh token path giới hạn: chỉ gửi cho endpoint `/api/auth/refresh`

---

## 7. Agent Engine

### Kiến trúc executor

```python
# agents/executor.py

execute_agent_stream(agent, messages, db) -> AsyncGenerator[AgentStreamEvent]
    │
    ├── build_llm_from_agent(agent)          # Tạo LLM instance qua provider.py
    ├── build_agent_tools(agent, db)         # Build tools + RAG retrieval tool
    │   ├── tool_registry.build_many()       # Custom tools
    │   └── KnowledgeRetriever.retrieve()    # RAG search tool
    ├── _build_history(messages, system_prompt)  # DB messages → LangChain messages
    │
    └── Nếu có tools:
        │   create_react_agent(llm, tools)   # LangGraph ReAct agent
        │   graph.astream_events(messages)   # Stream events
        └── Nếu không có tools:
            llm.astream(messages)            # Stream trực tiếp
```

### Sự kiện streaming

| Event | Mô tả | Data |
|-------|-------|------|
| `token` | Token mới từ LLM | `{content: "..."}` |
| `tool_start` | Bắt đầu gọi tool | `{name: "...", input: "..."}` |
| `tool_end` | Tool trả kết quả | `{name: "...", result: "..."}` |
| `done` | Hoàn thành | `{}` |
| `error` | Lỗi | `{message: "..."}` |

---

## 8. Tool Registry

### Kiến trúc builder pattern

```
ToolRegistry (singleton)
    │
    ├── HTTPRequestToolBuilder
    │   └── HTTP request với template variables {key} trong URL/body
    │
    ├── CodeExecToolBuilder
    │   └── Chạy Python code trong subprocess (temp file)
    │
    ├── WebScrapeToolBuilder
    │   └── GET URL, trả về text content (giới hạn max_length)
    │
    └── DBQueryToolBuilder
        └── SELECT-only query qua asyncpg (chặn INSERT/UPDATE/DELETE/DROP)
```

### Luồng build tool

```
Tool (DB record)
    → ToolRegistry.build(tool_def)
    → Builder tương ứng theo tool_type
    → json_schema_to_pydantic(input_schema)     # JSON Schema → Pydantic model
    → StructuredTool.from_function(coroutine, name, description, args_schema)
    → LangChain StructuredTool (sẵn sàng cho LLM gọi)
```

### Bảo mật DB Query tool

- Chỉ cho phép câu lệnh bắt đầu bằng `SELECT`
- Chặn từ khóa: `INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, GRANT, REVOKE`
- Giới hạn số dòng trả về (`max_rows`, mặc định 50)

---

## 9. RAG Pipeline

### Kiến trúc

```
Upload file
    → DocumentParser (PDF/DOCX/TXT/MD/CSV/HTML)
    → RecursiveCharacterTextSplitter (chunk_size=1000, overlap=200)
    → OpenAI Embeddings (text-embedding-3-small, 1536 chiều)
    → pgvector (lưu vector vào document_chunks.embedding)

Query
    → Embed câu hỏi → vector 1536 chiều
    → pgvector cosine distance search (top_k=5, threshold=0.7)
    → Trả về chunks có điểm tương đồng cao nhất
```

### Tích hợp với Agent

Khi agent có knowledge_bases được gắn:
- Tự động tạo tool `search_knowledge_base(query: str) -> str`
- LLM tự quyết định khi nào cần gọi tool này
- Tool thực hiện semantic search và trả về chunks liên quan

---

## 10. Workflow Engine

### Các loại node

| Node Type | Chức năng | Config chính |
|-----------|----------|-------------|
| `input` | Điểm bắt đầu, nhận dữ liệu đầu vào | - |
| `output` | Điểm kết thúc, đánh dấu kết quả | - |
| `llm` | Gọi LLM (OpenAI/Anthropic/Ollama) | llm_provider, llm_model, system_prompt, temperature |
| `tool` | Thực thi tool từ registry | tool_id |
| `condition` | Routing có điều kiện | condition_expression (Python eval) |
| `human_input` | Chờ input từ user | prompt_message, input_key, default_value |

### Compiler flow

```
Workflow (DB)
    → _build_adjacency(nodes, edges)          # Đồ thị kề
    → _find_start_node()                      # Tìm node "input" hoặc node không có edge vào
    → StateGraph(WorkflowState)               # Tạo LangGraph graph
    → Đăng ký nodes (async functions)
    → Đăng ký edges:
        - Thường: add_edge(src, dst)
        - Condition: add_conditional_edges(src, router_fn, path_map)
    → graph.compile()                         # Graph sẵn sàng invoke
    → graph.ainvoke(initial_state)            # Thực thi
```

### WorkflowState

```python
class WorkflowState(TypedDict):
    data: Any                    # Dữ liệu truyền giữa nodes
    output: Any                  # Kết quả cuối (set bởi output node)
    node_logs: list[dict]        # Log thực thi từng node
    total_tokens: int            # Tổng token sử dụng
    _condition_result: bool      # Kết quả condition (nội bộ)
    _initial_input: dict         # Input ban đầu (cho human_input)
```

---

## 11. Multi-Agent

### Supervisor Pattern

```
                    ┌──────────────┐
                    │  Supervisor  │ ◄── Quyết định routing
                    │   (LLM)     │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ Worker A │ │ Worker B │ │ Worker C │
        │  (Agent) │ │  (Agent) │ │  (Agent) │
        └──────────┘ └──────────┘ └──────────┘
              │            │            │
              └────────────┼────────────┘
                           │
                    ┌──────▼───────┐
                    │  Supervisor  │ ◄── Đánh giá, tiếp tục hoặc FINISH
                    └──────────────┘
```

- Supervisor parse response format `ROUTE: <worker_name>` hoặc `ROUTE: FINISH`
- Giới hạn `max_iterations` chống loop vô hạn
- Mỗi worker thực thi độc lập với tools riêng

### Peer Collaboration

```
User Message → Agent A → Agent B → Agent C → [Synthesis] → Kết quả
                 │           │          │
                 └─ context ─┘─ context ┘
```

- Agents xử lý tuần tự, mỗi agent nhận output agent trước làm context
- Tùy chọn node tổng hợp cuối (`synthesis_prompt`)
- Phù hợp cho: debate, review chain, pipeline xử lý nhiều bước

---

## 12. LLM Provider Abstraction

### Unified Interface

```python
# llm/provider.py

build_llm(provider, model, temperature, max_tokens, base_url) -> BaseChatModel
```

### Providers hỗ trợ

| Provider | Import | Ghi chú |
|----------|--------|---------|
| OpenAI | `langchain_openai.ChatOpenAI` | Mặc định, hỗ trợ base_url tùy chỉnh |
| Anthropic | `langchain_anthropic.ChatAnthropic` | Claude models |
| Ollama | `langchain_ollama.ChatOllama` | Local, base_url mặc định `http://localhost:11434` |

### Models mặc định

```python
DEFAULT_MODELS = {
    "openai": "gpt-4o",
    "anthropic": "claude-sonnet-4-20250514",
    "ollama": "llama3.1",
}
```

---

## 13. WebSocket Streaming

### Protocol

```
# Kết nối
WS /api/ws/chat/{conversation_id}?token=<jwt>

# Xác thực
1. Đọc token từ query param hoặc cookie
2. Giải mã JWT, kiểm tra type="access"
3. Accept hoặc close(4001)

# Client → Server
{"content": "Nội dung tin nhắn"}

# Server → Client
{"type": "token", "content": "từng"}           # Token LLM
{"type": "token", "content": " token"}
{"type": "tool_start", "name": "search", "input": "query"}  # Tool bắt đầu
{"type": "tool_end", "name": "search", "result": "..."}     # Tool kết thúc
{"type": "done"}                                             # Hoàn thành
{"type": "error", "message": "Chi tiết lỗi"}                # Lỗi
```

### Xử lý phía server

```python
while True:
    data = await ws.receive_json()           # Nhận tin nhắn
    await save_message(db, role="user")      # Lưu vào DB
    
    async for event in execute_agent_stream():
        await ws.send_json(event.to_dict())  # Stream events
    
    await save_message(db, role="assistant") # Lưu phản hồi
```

---

## 14. Triển khai & Docker

### Docker Compose

```yaml
services:
  postgres:     # pgvector/pgvector:pg16, port 5432
  backend:      # Python 3.12, port 8000, hot reload
  frontend:     # Node 20, port 3000, hot reload
```

### Biến môi trường

**Backend (.env)**

| Biến | Mô tả | Mặc định |
|------|-------|---------|
| DATABASE_URL | PostgreSQL async URL | `postgresql+asyncpg://postgres:postgres@localhost:5432/lc_agent` |
| SECRET_KEY | JWT signing key | (cần thay đổi) |
| ACCESS_TOKEN_EXPIRE_MINUTES | TTL access token | 30 |
| REFRESH_TOKEN_EXPIRE_DAYS | TTL refresh token | 7 |
| OPENAI_API_KEY | OpenAI API key | "" |
| ANTHROPIC_API_KEY | Anthropic API key | "" |
| UPLOAD_DIR | Thư mục lưu file | "uploads" |
| CORS_ORIGINS | Allowed origins | `["http://localhost:3000"]` |

**Frontend (.env.local)**

| Biến | Mô tả | Mặc định |
|------|-------|---------|
| NEXT_PUBLIC_API_URL | URL backend API | `http://localhost:8000/api` |
| NEXT_PUBLIC_WS_URL | URL WebSocket | `ws://localhost:8000/api` |

---

## 15. Quyết định thiết kế

| Quyết định | Lựa chọn | Lý do |
|-----------|----------|-------|
| Agent framework | LangGraph | Kiểm soát luồng rõ ràng, hỗ trợ checkpointing, subgraph |
| Vector store | pgvector trong PostgreSQL | Một DB duy nhất cho cả relational + vector, giảm phức tạp vận hành |
| Tool config | JSONB | Schema linh hoạt theo tool_type, validate ở tầng app bằng Pydantic |
| State management | Zustand (UI) + TanStack Query (server) | Tách biệt client/server state, tránh sync issues |
| Workflow editor | React Flow (@xyflow/react) | Chuẩn công nghiệp (Flowise, LangFlow đều dùng) |
| Auth | JWT + HTTP-only Cookie | Bảo mật CSRF, tự động refresh, không lưu token trong localStorage |
| Async Python | asyncpg + SQLAlchemy async | Non-blocking DB + LLM calls, đồng thời cao |
| Multi-agent | Supervisor + Peer | Hai pattern phổ biến nhất, đủ linh hoạt cho nhiều use case |

---

## Quy tắc cập nhật tài liệu

1. **Thêm module mới** → Cập nhật sơ đồ cấu trúc + mô tả module
2. **Thêm model/bảng** → Cập nhật sơ đồ quan hệ + chi tiết bảng
3. **Thêm API endpoint** → Cập nhật README.md
4. **Thay đổi luồng dữ liệu** → Cập nhật mục Luồng dữ liệu
5. **Thêm LLM provider** → Cập nhật mục LLM Provider Abstraction
6. **Thêm tool type** → Cập nhật mục Tool Registry
7. **Thêm node type** → Cập nhật mục Workflow Engine

> **Nguyên tắc**: Cập nhật docs trước, implement sau.
