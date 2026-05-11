# Development Guide

This document is for developers contributing to or self-hosting AgentForge. For a product
overview, see [README.md](README.md).

## Table of Contents

- [Prerequisites](#prerequisites)
- [Project Structure](#project-structure)
- [Local Setup](#local-setup)
- [Using the `forge` CLI](#using-the-forge-cli)
- [Manual Setup (without the CLI)](#manual-setup-without-the-cli)
- [Environment Variables](#environment-variables)
- [Database Migrations](#database-migrations)
- [API Overview](#api-overview)
- [Operational Endpoints](#operational-endpoints)
- [Operator CLIs](#operator-clis)
- [Production Hardening](#production-hardening)
- [Documentation](#documentation)
- [Conventions Cheat Sheet](#conventions-cheat-sheet)

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & Docker Compose v2
- [Node.js](https://nodejs.org/) 20+ and [pnpm](https://pnpm.io/)
- [Python](https://www.python.org/) 3.12+
- An LLM API key (OpenAI / Anthropic / or Ollama for fully local)

---

## Project Structure

```text
lc-agent/
├── apps/
│   ├── backend/             FastAPI + LangGraph (4-layer modules: router → service → model → schema)
│   └── frontend/            Next.js 16 (feature-based, thin App Router)
├── services/
│   ├── postgres/            pgvector:pg16
│   ├── redis/               redis:7-alpine
│   ├── rabbitmq/            rabbitmq:3-management
│   ├── dispatcher/          Background job dispatcher
│   ├── code-sandbox/        Sandboxed code execution
│   ├── mail/                Outbound + IMAP inbound mail
│   └── socket/              WebSocket gateway
├── docs/                    Source-of-truth specifications (60+ files)
├── mcp-docs/                MCP server for AI-assisted doc search
├── scripts/
│   ├── forge.sh             CLI for Linux/Mac/Git Bash
│   └── forge.cmd            CLI for Windows
├── docker-compose.yml       Root orchestration
├── docker-compose.dev.yml   Dev overrides (hot-reload)
├── CLAUDE.md                AI assistant context
├── README.md                Product overview
└── DEVELOPMENT.md           This file
```

### Backend modules (`apps/backend/app/`)

`agents`, `workflows`, `multi_agent`, `knowledge`, `tools`, `conversations`, `auth`, `mfa`, `sso`,
`scim`, `billing`, `payments`, `payouts`, `usage`, `hub`, `webhooks`, `email_triggers`,
`slack_triggers`, `discord_triggers`, `teams_triggers`, `scheduled_triggers`, `notifications`,
`observability`, `audit`, `admin`, `workspaces`, `integrations`, `personal_tokens`,
`ai_credentials`, `share`, `permissions`, `storage`, `uploads`, `extractors`, `llm`, `jobs`,
`dashboard`, `external`, `internal`, `security`.

### Frontend features (`apps/frontend/src/features/`)

`agents`, `workflows`, `chat`, `knowledge`, `tools`, `triggers`, `integrations`, `hub`, `billing`,
`usage`, `notifications`, `admin`, `settings`, `workspaces`, `onboarding`, `landing`, `dashboard`,
`jobs`, `auth`.

---

## Local Setup

### Full Docker Stack (easiest)

```bash
git clone <repo-url> lc-agent
cd lc-agent

# Configure
cp apps/backend/.env.example apps/backend/.env
cp apps/frontend/.env.example apps/frontend/.env.local
# Edit apps/backend/.env → set OPENAI_API_KEY (and/or ANTHROPIC_API_KEY)

# Start
docker compose up -d
docker compose exec backend alembic upgrade head

# Bootstrap admin user (idempotent — promotes if email exists)
docker compose exec backend python -m app.cli.seed_admin \
    --email admin@example.com --password 'ChangeMe!'

# Seed the 5 official starter templates (used by the /welcome wizard)
docker compose exec backend python -m app.cli.seed_starter_templates \
    --owner-email admin@example.com
```

| Service         | URL                                        |
| --------------- | ------------------------------------------ |
| **Frontend**    | <http://localhost:3000>                    |
| **API Swagger** | <http://localhost:8000/api/docs>           |
| **API OpenAPI** | <http://localhost:8000/api/openapi.json>   |
| **RabbitMQ UI** | <http://localhost:15672>                   |

### Hybrid (infra in Docker, apps local with hot-reload)

Recommended for daily development:

```bash
./scripts/forge.sh start infra        # postgres + redis + rabbitmq in Docker
./scripts/forge.sh install backend    # pip install -e ".[dev]"
./scripts/forge.sh migrate            # alembic upgrade head
./scripts/forge.sh dev backend        # uvicorn --reload on :8000

# In another terminal
./scripts/forge.sh install frontend   # pnpm install
./scripts/forge.sh dev frontend       # next dev on :3000
```

---

## Using the `forge` CLI

```bash
# Linux / Mac / Git Bash
./scripts/forge.sh <command> [target]

# Windows CMD / PowerShell
scripts\forge.cmd <command> [target]
```

### Command reference

| Command            | Description                          |
| ------------------ | ------------------------------------ |
| `start [target]`   | Start services via Docker            |
| `stop [target]`    | Stop services                        |
| `restart [target]` | Restart services                     |
| `build [target]`   | Build Docker images                  |
| `dev <target>`     | Start local dev server (hot-reload)  |
| `logs [target]`    | Tail logs                            |
| `status`           | Show running services                |
| `health`           | Hit `/healthz` and `/readyz`         |
| `install <target>` | Install dependencies                 |
| `test <target>`    | Run tests                            |
| `migrate`          | Run Alembic migrations               |
| `clean [target]`   | Remove containers + volumes          |

**Targets:** `all`, `infra`, `apps`, `postgres`, `redis`, `rabbitmq`, `backend`, `frontend`, `docs`

### Common workflows

```bash
# Start everything in Docker
./scripts/forge.sh start all
./scripts/forge.sh status
./scripts/forge.sh logs backend
./scripts/forge.sh stop all

# Run tests
./scripts/forge.sh test backend
./scripts/forge.sh test frontend
```

---

## Manual Setup (without the CLI)

### Backend

```bash
cd apps/backend
python -m venv .venv
source .venv/bin/activate           # Linux/Mac
# .venv\Scripts\activate            # Windows

pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd apps/frontend
pnpm install
pnpm dev
```

### Single service

```bash
cd services/postgres
docker compose up -d                # Start standalone
docker compose logs -f              # Tail logs
docker compose down -v              # Stop + remove data
```

---

## Environment Variables

### Backend (`apps/backend/.env`)

| Variable             | Default                              | Description                  |
| -------------------- | ------------------------------------ | ---------------------------- |
| `DATABASE_URL`       | `postgresql+asyncpg://...`           | Async DB connection          |
| `SECRET_KEY`         | `dev-secret-key...`                  | JWT signing key              |
| `OPENAI_API_KEY`     |                                      | OpenAI API key               |
| `ANTHROPIC_API_KEY`  |                                      | Anthropic API key            |
| `REDIS_URL`          | `redis://localhost:6379/0`           | Redis connection             |
| `RABBITMQ_URL`       | `amqp://guest:guest@localhost:5672/` | RabbitMQ connection          |
| `CORS_ORIGINS`       | `["http://localhost:3000"]`          | Allowed origins              |
| `STRIPE_SECRET_KEY`  |                                      | Stripe billing               |
| `LANGFUSE_PUBLIC_KEY`|                                      | Langfuse LLM tracing         |
| `LANGFUSE_SECRET_KEY`|                                      | Langfuse LLM tracing         |

### Frontend (`apps/frontend/.env.local`)

| Variable                | Default                          | Description       |
| ----------------------- | -------------------------------- | ----------------- |
| `NEXT_PUBLIC_API_URL`   | `http://localhost:8000/api`      | Backend API URL   |
| `NEXT_PUBLIC_WS_URL`    | `ws://localhost:8000/api`        | WebSocket URL     |

See `apps/backend/.env.example` and `apps/frontend/.env.example` for the full list.

---

## Database Migrations

```bash
cd apps/backend

# Create a new migration
alembic revision --autogenerate -m "add new field"

# Apply migrations
alembic upgrade head

# Rollback one
alembic downgrade -1

# Show current revision
alembic current
```

**Convention:** snake_case plural table names · UUID primary keys · JSONB for configs ·
pgvector for embeddings.

---

## API Overview

| Group             | Endpoints                                                                       |
| ----------------- | ------------------------------------------------------------------------------- |
| **Auth**          | `POST /api/auth/{register,login,refresh,logout}`, `GET /api/auth/me`            |
| **Agents**        | `CRUD /api/agents`, attach/detach tools & knowledge bases                       |
| **Tools**         | `CRUD /api/tools`, `POST /api/tools/{id}/test`                                  |
| **Knowledge**     | `CRUD /api/knowledge-bases`, upload documents, semantic query                   |
| **Workflows**     | `CRUD /api/workflows`, execute, run history, node logs                          |
| **Conversations** | `CRUD /api/conversations`, messages, `WS /api/ws/chat/{id}`                     |
| **Multi-Agent**   | `POST /api/multi-agent/{supervisor,peer}`, providers list                       |
| **Triggers**      | `POST /api/triggers/webhook/{id}`, email/slack/discord/teams inbound, scheduled |
| **Billing**       | `POST /api/billing/checkout`, subscriptions, usage, payouts                     |
| **Hub**           | Browse, install, publish templates                                              |
| **Admin**         | User/workspace management, audit logs, SSO/SCIM, MFA                            |

Full interactive API docs at <http://localhost:8000/api/docs> (Swagger UI).

---

## Operational Endpoints

| Path                    | Purpose                                                            |
| ----------------------- | ------------------------------------------------------------------ |
| `GET /healthz`          | Liveness — always 200, no deps. Use as Kubernetes `livenessProbe`. |
| `GET /readyz`           | Readiness — pings Postgres + Redis. Returns 503 when degraded.     |
| `GET /api/openapi.json` | Full OpenAPI spec for client codegen.                              |

---

## Operator CLIs

```bash
# Promote an existing user to admin without resetting their password
docker compose exec backend python -m app.cli.seed_admin \
    --email user@example.com --promote-only

# Refresh seeded starter templates after editing _starter_templates.py
docker compose exec backend python -m app.cli.seed_starter_templates \
    --owner-email admin@example.com
```

---

## Production Hardening

For production deployments, see:

- [`docs/architecture/operations.md`](docs/architecture/operations.md) — JSON logs, Sentry,
  Stripe Connect payouts, scaling guidance.
- [`docs/guides/momo-setup.md`](docs/guides/momo-setup.md) — Enabling VND payments via MoMo
  (Vietnam): merchant registration, env vars, IPN exposure, sandbox testing, author payout
  settlement.

Key recommendations:

- Set `SECRET_KEY` to a high-entropy value (e.g., `openssl rand -hex 64`)
- Run behind HTTPS (Caddy, Nginx, Traefik)
- Enable `JSON_LOGS=true` for structured logging
- Configure Sentry via `SENTRY_DSN`
- Scale `dispatcher` and `socket` services horizontally
- Use a managed Postgres (RDS, Cloud SQL, etc.) with daily backups

---

## Documentation

Project specifications live in [`docs/`](docs/) (60+ files organized by domain):

```text
docs/
├── architecture/    System design, project structure, deployment, dependencies
├── conventions/     Code style rules (backend, frontend, components, database, API)
├── backend/         Per-module specifications
├── frontend/        Per-feature specifications
├── database/        Per-table schema specifications
├── api/             Per-endpoint request/response examples
├── flows/           End-to-end flow specifications
└── guides/          Operator and integration how-tos
```

### MCP doc server for AI assistants

An MCP server at [`mcp-docs/`](mcp-docs/) provides searchable doc access for AI assistants
(Claude Code, Cursor, etc.):

```bash
./scripts/forge.sh dev docs   # Start MCP docs server
```

Once running, AI assistants can call `search_docs("query")`, `get_doc("doc-id")`,
`list_docs("domain")`, `get_schema("table_name")`, `get_api("/endpoint")`, and
`get_component("name")`.

---

## Conventions Cheat Sheet

Read [`CLAUDE.md`](CLAUDE.md) and [`docs/conventions/`](docs/conventions/) for the full set.

### Backend

- **4-layer modules**: `router.py` → `service.py` → `model.py` → `schema.py`
- **Async everywhere**: `async def`, `AsyncSession`, `httpx.AsyncClient`
- **Request context**: read `app.context.current_user_id()` from a `ContextVar` instead of
  threading `user_id` through every signature. Keep explicit only in: login flow
  (`auth/tokens.py`), workflow runner, ingestion pipeline, and webhook background tasks
  (anything reachable from `asyncio.create_task` outside an HTTP request). For background
  tasks that *do* need to inherit, wrap with `run_in_request_context(user_id, coro)`.
- **Database**: snake_case plural tables, UUID PKs, JSONB for configs, pgvector for embeddings

### Frontend

- **Feature-based architecture**: thin App Router pages, all logic in `features/<feature>/`
- **State**: TanStack Query for server state, Zustand for UI-only state
- **UI**: shadcn/ui on radix-ui (composed package). Components import from `radix-ui`,
  not `@base-ui/react`. `asChild` prop works as expected.
- **Auth**: JWT in httpOnly secure cookies — **never** localStorage
- **Styling**: Tailwind, prefer `buttonVariants()` for `<Link>` so the anchor stays a real `<a>`

### Theming

- Landing page: **light theme**, enterprise feel
- Dashboard: **dark theme** (`bg-[#08090a]`)
