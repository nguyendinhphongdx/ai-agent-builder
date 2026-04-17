---
id: arch-project-structure
title: Project Structure - Monorepo Layout
domain: architecture
tags: [project-structure, monorepo, apps, services, docs, directory-layout]
related: [arch-system-overview, arch-deployment, conventions-backend, conventions-frontend]
summary: Monorepo with apps/ (backend + frontend), services/ (postgres, redis, rabbitmq), docs/ (specifications), mcp-docs/ (MCP server).
---

# Project Structure

## Root Layout

```
lc-agent/
├── apps/
│   ├── backend/              # Python FastAPI application
│   └── frontend/             # Next.js 16 application
├── services/
│   ├── postgres/             # PostgreSQL + pgvector (own docker-compose)
│   ├── redis/                # Redis (own docker-compose)
│   └── rabbitmq/             # RabbitMQ (own docker-compose)
├── docs/                     # Source of truth - specifications
├── mcp-docs/                 # Node.js MCP server for doc search
├── docker-compose.yml        # Root orchestration
├── .mcp.json                 # Claude Code MCP config
├── CLAUDE.md                 # Auto-loaded by Claude Code
└── .gitignore
```

## Backend Structure (`apps/backend/`)

```
apps/backend/
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI app factory, router registration, WebSocket
│   ├── config.py              # Settings (pydantic-settings, env vars)
│   ├── db/
│   │   ├── base.py            # DeclarativeBase, UUIDMixin, TimestampMixin
│   │   └── session.py         # async_session_factory, get_db dependency
│   ├── models/                # SQLAlchemy ORM models (16 tables)
│   │   ├── user.py
│   │   ├── agent.py           # Agent + AgentTool + AgentKnowledgeBase
│   │   ├── tool.py
│   │   ├── knowledge_base.py
│   │   ├── document.py
│   │   ├── document_chunk.py  # pgvector embedding column
│   │   ├── workflow.py
│   │   ├── workflow_node.py
│   │   ├── workflow_edge.py
│   │   ├── workflow_run.py
│   │   ├── conversation.py
│   │   ├── message.py
│   │   └── api_key.py
│   ├── auth/                  # router.py, service.py, schemas.py, dependencies.py
│   ├── agents/                # router.py, service.py, schemas.py, executor.py
│   ├── tools/                 # router.py, service.py, schemas.py, registry.py
│   │   └── builtins/          # Built-in tool builders
│   ├── knowledge/             # router.py, service.py, schemas.py, ingestion.py, retriever.py
│   ├── workflows/             # router.py, service.py, schemas.py, compiler.py
│   │   └── nodes/             # Node type executors
│   ├── conversations/         # router.py, service.py, schemas.py, ws.py
│   ├── multi_agent/           # router.py, supervisor.py, peer.py, schemas.py
│   ├── llm/                   # provider.py (LLM factory)
│   └── storage/               # base.py (file upload)
├── alembic/                   # Database migrations
├── pyproject.toml
├── Dockerfile
├── .env.example
└── .env
```

## Frontend Structure (`apps/frontend/`)

```
apps/frontend/
├── src/
│   ├── app/                   # Next.js App Router (THIN pages)
│   │   ├── layout.tsx         # Root layout + Providers
│   │   ├── page.tsx           # Landing page (public, light theme)
│   │   ├── (auth)/
│   │   │   ├── login/page.tsx
│   │   │   └── register/page.tsx
│   │   └── (dashboard)/
│   │       ├── layout.tsx     # Sidebar + Header + auth guard
│   │       ├── page.tsx       # Redirect to /libraries
│   │       ├── libraries/page.tsx
│   │       ├── agents/new/page.tsx
│   │       ├── agents/[id]/page.tsx
│   │       ├── agents/[id]/chat/page.tsx
│   │       ├── tools/page.tsx
│   │       ├── knowledge/page.tsx
│   │       ├── workflows/page.tsx
│   │       ├── workflows/[id]/page.tsx
│   │       └── settings/page.tsx
│   ├── features/              # Feature modules
│   │   ├── auth/              # views/, components/, hooks/, services/, types/
│   │   ├── agents/
│   │   ├── chat/
│   │   ├── tools/
│   │   ├── knowledge/
│   │   ├── workflows/
│   │   ├── dashboard/
│   │   └── settings/
│   ├── components/
│   │   ├── ui/                # shadcn/ui components
│   │   ├── layout/            # Sidebar.tsx, Header.tsx
│   │   ├── shared/            # LoadingState, EmptyState
│   │   └── providers/         # Providers.tsx, QueryProvider, ThemeProvider
│   ├── lib/
│   │   ├── api/               # client.ts (Axios), endpoints.ts
│   │   ├── ws/                # client.ts (WebSocket)
│   │   └── utils.ts           # cn() helper
│   └── hooks/                 # Shared hooks
├── package.json
├── tailwind.config.ts
├── next.config.ts
└── tsconfig.json
```

## Service Structure (each service)

```
services/{service-name}/
├── docker-compose.yml         # Standalone docker-compose
├── .env.example               # Environment variables template
├── .env                       # Actual env (gitignored)
└── init/                      # Optional init scripts
```

Each service can run independently: `cd services/postgres && docker compose up`
Or all together from root: `docker compose up`
