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

The backend is organised into **5 top-level packages** under `app/`. Feature
modules live in `modules/`, grouped into 7 buckets by purpose (build-time vs
runtime vs identity, etc.). Engines, infra, and the ORM registry sit beside
`modules/` rather than under it.

```
apps/backend/
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI app factory, router registration, WebSocket
│   │
│   ├── core/                 # Engines (heavy runtime code, not HTTP-shaped)
│   │   ├── workflow_runner.py
│   │   ├── retrieval.py
│   │   ├── ingestion.py
│   │   └── kb_connectors/
│   │
│   ├── background/           # Async loops — each implements start()/stop() ABC
│   │   ├── audit_purge.py
│   │   ├── billing_reporter.py
│   │   ├── email_poll.py
│   │   ├── kb_sync.py
│   │   └── scheduled_triggers.py
│   │
│   ├── platform/             # Cross-cutting infrastructure
│   │   ├── config.py          # Settings (pydantic-settings, env vars)
│   │   ├── context.py         # Request-scoped ContextVars (user_id, workspace_id)
│   │   ├── db/                # base.py, session.py
│   │   ├── security/          # JWT, password hashing, dependencies
│   │   ├── storage/           # File upload backend
│   │   ├── observability/     # Logging, Sentry, OTEL
│   │   ├── permissions/       # Role / workspace gating
│   │   ├── schemas/           # Shared pydantic primitives
│   │   ├── extractors/        # File text extraction
│   │   ├── cli/               # Operator CLIs (seed_admin, seed_starter_templates)
│   │   ├── rate_limit/        # Redis-backed limiter
│   │   └── dispatcher_client/ # External dispatcher RPC
│   │
│   ├── models/               # SQLAlchemy ORM registry (flat — alembic depends on this)
│   │   ├── user.py
│   │   ├── agent.py
│   │   ├── ...               # one file per table
│   │
│   └── modules/              # Feature modules grouped into 7 buckets
│       ├── studio/           # What users BUILD
│       │   ├── agents/       # (+ orchestration/ for supervisor + peer multi-agent)
│       │   ├── workflows/
│       │   ├── knowledge/
│       │   ├── tools/
│       │   └── plugins/
│       │
│       ├── runtime/          # HOW things activate / interact
│       │   ├── chat/         # conversations/, share/, annotations/
│       │   ├── triggers/     # scheduled/, email/, slack/, teams/, discord/, http/
│       │   ├── jobs/
│       │   ├── notifications/
│       │   └── uploads/
│       │
│       ├── identity/         # WHO can act
│       │   ├── auth/         # (+ mfa/, sso/, scim/)
│       │   ├── workspaces/
│       │   └── tokens/       # personal access tokens
│       │
│       ├── integrations/     # External systems we plug into
│       │   ├── connectors/   # oauth/, kb/
│       │   ├── llm/          # (+ credentials/ for ai_credentials)
│       │   └── mcp/
│       │
│       ├── commerce/         # Money flow
│       │   ├── payments/     # subscriptions/, checkout/, payouts/
│       │   ├── usage/
│       │   └── hub/          # marketplace
│       │
│       ├── ops/              # Operational visibility
│       │   ├── audit/
│       │   └── dashboard/
│       │
│       └── api/              # Audience layers
│           ├── external/     # public API
│           ├── internal/     # jobs-callback / service-to-service
│           └── admin/
├── alembic/                  # Database migrations
├── pyproject.toml
├── Dockerfile
├── .env.example
└── .env
```

### Bucket rationale

| Bucket | Question it answers | Contents |
| --- | --- | --- |
| `studio/` | What users **build** | agents, workflows, knowledge bases, tools, plugins |
| `runtime/` | **How** things activate / interact | chat, triggers, jobs, notifications, uploads |
| `identity/` | **Who** can act | auth (+ mfa, sso, scim), workspaces, tokens |
| `integrations/` | External systems we plug into | connectors (oauth, kb), llm, mcp |
| `commerce/` | Money flow | payments (subs, checkout, payouts), usage, hub |
| `ops/` | Operational visibility | audit, dashboard |
| `api/` | Audience layers | external (public), internal (jobs callback), admin |

### Import conventions

- Feature code: `from app.modules.<bucket>.<feature> import service` — e.g.
  `app.modules.studio.agents.service`, `app.modules.runtime.chat.conversations.ws`.
- Infrastructure: `from app.platform.<area> import ...` — e.g.
  `app.platform.config`, `app.platform.db.session`, `app.platform.context`.
- Engines: `from app.core.<engine> import ...` — e.g. `app.core.workflow_runner`,
  `app.core.retrieval`.
- Background loops: `from app.background.<loop> import ...` — e.g.
  `app.background.kb_sync`.
- ORM models stay flat at `app.models.<table>` because alembic autogenerate
  scans a single registry.

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
