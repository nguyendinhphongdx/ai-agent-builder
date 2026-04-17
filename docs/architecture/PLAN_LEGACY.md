# AI Agent Builder - Implementation Plan

## Context
Build an AI Agent Builder platform (similar to Dify/Flowise) using Python FastAPI + LangChain/LangGraph backend and Next.js frontend. The system allows users to create custom AI agents with tools, knowledge bases, visual workflows, and multi-agent collaboration.

## Tech Stack
- **Backend**: Python 3.12 + FastAPI + LangChain + LangGraph
- **Frontend**: Next.js 14 (App Router) + TypeScript + Tailwind + shadcn/ui
- **Database**: PostgreSQL + pgvector (vector embeddings)
- **State management**: Zustand
- **Workflow editor**: React Flow
- **Auth**: JWT (access + refresh tokens)
- **Containerization**: Docker Compose

## Architecture Overview

```
User -> Next.js Frontend -> FastAPI REST/WebSocket -> LangGraph Engine
                                    |                       |
                                    v                       v
                              PostgreSQL          LLM Providers (OpenAI, Anthropic)
                            (data + pgvector)
```

## Project Structure

```
lc-agent/
├── backend/
│   ├── alembic/                    # DB migrations
│   ├── app/
│   │   ├── main.py                 # FastAPI app
│   │   ├── config.py               # pydantic-settings
│   │   ├── auth/                   # JWT auth
│   │   ├── models/                 # SQLAlchemy ORM
│   │   ├── agents/                 # Agent CRUD + executor
│   │   ├── tools/                  # Custom tool management + registry
│   │   │   └── builtins/           # http_request, code_exec, db_query, web_scrape
│   │   ├── knowledge/              # RAG pipeline (ingestion, embedding, retrieval)
│   │   ├── workflows/              # Visual workflow compiler (JSON -> LangGraph)
│   │   │   └── nodes/              # llm, tool, condition, human_input, subgraph
│   │   ├── conversations/          # Chat history + WebSocket streaming
│   │   ├── multi_agent/            # Supervisor + peer collaboration patterns
│   │   ├── llm/                    # LLM provider abstraction
│   │   ├── storage/                # File storage (local/S3)
│   │   └── db/                     # Session + base model
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/                    # Next.js App Router pages
│   │   ├── components/             # UI, chat, workflow editor, knowledge
│   │   ├── lib/                    # API client, WebSocket, auth helpers
│   │   ├── stores/                 # Zustand stores
│   │   └── types/                  # TypeScript interfaces
│   ├── package.json
│   └── tailwind.config.ts
└── docker-compose.yml
```

## Database Models

### Core Tables
- **users**: email, hashed_pw, full_name, is_active
- **agents**: name, system_prompt, llm_provider, llm_model, llm_config (JSONB)
- **tools**: name, description, tool_type, config (JSONB), input_schema (JSONB)
- **knowledge_bases**: name, embedding_provider, chunk_size, chunk_overlap
- **documents**: filename, file_path, file_type, status (pending/processing/ready/failed)
- **document_chunks**: content, embedding (vector(1536)), metadata (JSONB), chunk_index
- **workflows**: name, description, is_active
- **workflow_nodes**: node_type, config (JSONB), position_x/y
- **workflow_edges**: source_node_id, target_node_id, condition (JSONB)
- **conversations**: agent_id, title, metadata
- **messages**: role, content, tool_calls (JSONB), token_usage (JSONB)

### Junction Tables
- **agent_tools**: agent_id, tool_id
- **agent_knowledge_bases**: agent_id, knowledge_base_id

## API Endpoints

### Auth
```
POST   /api/auth/register
POST   /api/auth/login              -> {access_token, refresh_token}
POST   /api/auth/refresh
```

### Agents
```
GET    /api/agents
POST   /api/agents
GET    /api/agents/{id}
PUT    /api/agents/{id}
DELETE /api/agents/{id}
POST   /api/agents/{id}/tools/{tool_id}
DELETE /api/agents/{id}/tools/{tool_id}
POST   /api/agents/{id}/knowledge-bases/{kb_id}
DELETE /api/agents/{id}/knowledge-bases/{kb_id}
```

### Tools
```
GET    /api/tools
POST   /api/tools
GET    /api/tools/{id}
PUT    /api/tools/{id}
DELETE /api/tools/{id}
POST   /api/tools/{id}/test
```

### Knowledge Bases
```
GET    /api/knowledge-bases
POST   /api/knowledge-bases
GET    /api/knowledge-bases/{id}
DELETE /api/knowledge-bases/{id}
POST   /api/knowledge-bases/{id}/documents      # Upload file(s)
GET    /api/knowledge-bases/{id}/documents
DELETE /api/knowledge-bases/{id}/documents/{doc_id}
POST   /api/knowledge-bases/{id}/query           # Test retrieval
```

### Workflows
```
GET    /api/workflows
POST   /api/workflows
GET    /api/workflows/{id}
PUT    /api/workflows/{id}                       # Save graph (nodes + edges)
DELETE /api/workflows/{id}
POST   /api/workflows/{id}/execute
GET    /api/workflows/{id}/runs/{run_id}
```

### Conversations + Chat
```
GET    /api/conversations
POST   /api/conversations
GET    /api/conversations/{id}/messages
POST   /api/conversations/{id}/messages
WS     /api/ws/chat/{conversation_id}            # Streaming
```

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent framework | LangGraph | Explicit control flow, checkpointing, subgraph composition. Plain AgentExecutor is deprecated |
| Vector store | pgvector | Single DB for relational + vector data, less operational complexity |
| Tool config storage | JSONB | Flexible schema per tool type, validation at app layer via Pydantic |
| Workflow editor | React Flow | Industry standard for node-based editors (used by Flowise, LangFlow) |
| State management | Zustand | Lighter than Redux, works well with App Router |

## Core Components

### 1. Tool Registry (`backend/app/tools/registry.py`)
Converts DB tool definitions -> LangChain `StructuredTool` at runtime. Builder pattern per tool_type. `json_schema_to_pydantic()` for dynamic args_schema.

### 2. RAG Pipeline (`backend/app/knowledge/`)
Upload -> Parse (PDF/TXT/MD/DOCX) -> Chunk (`RecursiveCharacterTextSplitter`) -> Embed -> Store in pgvector. Auto-creates `search_knowledge` tool for agents with KBs attached.

### 3. Workflow Compiler (`backend/app/workflows/compiler.py`)
JSON graph definition -> LangGraph `StateGraph`. Maps node types to async handler functions. Conditional edges for routing. Uses LangGraph checkpointer for state persistence.

### 4. Multi-Agent (`backend/app/multi_agent/`)
- **Supervisor pattern**: supervisor LLM routes tasks to worker agents
- **Peer collaboration**: agents pass messages in sequence (debate/review chain)

### 5. WebSocket Streaming (`backend/app/conversations/ws.py`)
Uses LangGraph `astream_events` v2. Protocol:
- Server -> Client: `{type: "token"|"tool_start"|"tool_end"|"done", ...}`
- Client -> Server: `{content: string}`

## Implementation Phases

### Phase 1 - Foundation
1. Project scaffolding (FastAPI + Next.js + Docker Compose with Postgres)
2. Database models + Alembic migrations
3. Auth module (register, login, JWT)
4. Agent CRUD (API + frontend pages)
5. Simple chat with WebSocket streaming (single agent, no tools)

### Phase 2 - Tools + RAG
6. Tool CRUD + ToolRegistry + HTTP request builder
7. Agent executor with LangGraph `create_react_agent` for tool-calling
8. Knowledge base CRUD + file upload
9. Document ingestion pipeline (parse, chunk, embed, pgvector)
10. Auto-attach retrieval tool to agents with KBs

### Phase 3 - Visual Workflows
11. Workflow CRUD (save/load graph JSON)
12. WorkflowCompiler: JSON -> LangGraph StateGraph
13. Node type implementations (LLM, tool, condition, human-input)
14. React Flow canvas + node palette in frontend
15. Workflow execution + run tracking

### Phase 4 - Multi-Agent + Polish
16. Supervisor orchestrator
17. Peer collaboration pattern
18. Multi-agent UI
19. Additional tool types (code exec sandbox, DB query, web scraper)
20. Additional LLM providers (Anthropic, Ollama)

## Verification
- `docker-compose up` -> all services start
- Auth flow: register -> login -> get token
- Create agent -> chat via WebSocket -> verify streaming
- Create tool -> attach to agent -> verify tool calling
- Upload document -> verify chunks in DB -> test retrieval
- Build workflow in visual editor -> execute -> verify step-by-step
- Configure supervisor + workers -> test multi-agent delegation
