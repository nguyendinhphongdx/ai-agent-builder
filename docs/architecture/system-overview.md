---
id: arch-system-overview
title: System Overview - Tech Stack & Data Flow
domain: architecture
tags: [architecture, tech-stack, data-flow, fastapi, nextjs, langchain, langgraph, pgvector]
related: [arch-project-structure, arch-deployment, arch-dependencies]
summary: High-level system architecture. FastAPI backend + Next.js 16 frontend + PostgreSQL/pgvector. LangGraph for agent orchestration. JWT httpOnly cookies for auth.
---

# System Overview

## Architecture Diagram

```
User Browser
    │
    ├── GET pages ──→ Next.js 16 (App Router, SSR/SSG)
    │                   port 3000
    │
    └── API calls ──→ FastAPI (REST + WebSocket)
          (cookies)     port 8000
                          │
                          ├── LangGraph ──→ LLM Providers
                          │   (agent orchestration)  (OpenAI, Anthropic, Ollama)
                          │
                          ├── SQLAlchemy ──→ PostgreSQL 16 + pgvector
                          │   (async ORM)     port 5432
                          │
                          ├── Redis ──→ Cache, sessions (future)
                          │              port 6379
                          │
                          └── RabbitMQ ──→ Background tasks (future)
                                           port 5672
```

## Tech Stack

### Backend
| Technology | Version | Purpose |
|---|---|---|
| Python | 3.12+ | Runtime |
| FastAPI | 0.115+ | Web framework (async) |
| SQLAlchemy | 2.0+ | ORM (async mode) |
| Alembic | 1.14+ | Database migrations |
| LangChain | 0.3+ | LLM tools, embeddings, text splitters |
| LangGraph | 0.2+ | Agent orchestration, workflow execution |
| asyncpg | 0.30+ | PostgreSQL async driver |
| pgvector | 0.3+ | Vector similarity search |
| python-jose | 3.3+ | JWT token handling |
| passlib | 1.7+ | Password hashing (bcrypt) |

### Frontend
| Technology | Version | Purpose |
|---|---|---|
| Next.js | 16.x | React framework (App Router) |
| React | 19.x | UI library |
| TypeScript | 5.x | Type safety |
| Tailwind CSS | 4.x | Styling |
| shadcn/ui | latest | Component library (@base-ui/react) |
| TanStack Query | 5.x | Server state management |
| Zustand | 5.x | Client state management |
| @xyflow/react | 12.x | Workflow visual editor (React Flow) |
| Axios | 1.x | HTTP client |

### Infrastructure
| Technology | Purpose |
|---|---|
| PostgreSQL 16 + pgvector | Primary database + vector embeddings |
| Redis 7 | Caching, session store (future) |
| RabbitMQ 3 | Message queue for background tasks (future) |
| Docker Compose | Container orchestration |

## Data Flow

### Chat Request Flow
1. User sends message via WebSocket
2. FastAPI receives, saves user message to DB
3. Load agent config + tools + knowledge bases
4. Build LangGraph `create_react_agent` with tools
5. Stream response via `astream_events` v2
6. Each token sent to client via WebSocket
7. Tool calls shown as `tool_start`/`tool_end` events
8. Final response saved to DB
9. Client receives `done` event

### Authentication Flow
1. User registers/logs in via POST
2. Server generates JWT access_token (30min) + refresh_token (7 days)
3. Tokens set as httpOnly secure cookies (NOT localStorage)
4. Every request auto-sends cookies (withCredentials: true)
5. On 401, Axios interceptor calls /auth/refresh automatically
6. Refresh rotates both tokens
