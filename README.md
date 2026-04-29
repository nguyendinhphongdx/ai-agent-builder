# AgentForge

Open-source AI Agent Builder platform. Create, configure, and deploy AI agents with custom tools, knowledge bases (RAG), visual workflows, and multi-agent collaboration.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, LangChain, LangGraph |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind, shadcn/ui |
| Database | PostgreSQL 16 + pgvector |
| Workflow Editor | React Flow (@xyflow/react v12) |
| State | TanStack Query (server) + Zustand (UI) |
| Auth | JWT in httpOnly secure cookies |
| Infra | Docker Compose, Redis, RabbitMQ |

## Project Structure

```
lc-agent/
├── apps/
│   ├── backend/            Python FastAPI + LangGraph
│   └── frontend/           Next.js 16 + TypeScript
├── services/
│   ├── postgres/           pgvector:pg16 (own docker-compose)
│   ├── redis/              redis:7-alpine
│   └── rabbitmq/           rabbitmq:3-management
├── docs/                   Project specifications (59 files)
├── mcp-docs/               MCP server for doc search
├── scripts/
│   ├── forge.sh            CLI for Linux/Mac/Git Bash
│   └── forge.cmd           CLI for Windows
├── docker-compose.yml      Root orchestration
├── docker-compose.dev.yml  Dev overrides (hot-reload)
└── CLAUDE.md               AI assistant context
```

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & Docker Compose v2
- [Node.js](https://nodejs.org/) 20+ & [pnpm](https://pnpm.io/)
- [Python](https://www.python.org/) 3.12+
- OpenAI API key (or Anthropic / Ollama for local)

## Quick Start

```bash
# 1. Clone
git clone <repo-url>
cd lc-agent

# 2. Copy environment files
cp apps/backend/.env.example apps/backend/.env
cp apps/frontend/.env.example apps/frontend/.env.local
# Edit apps/backend/.env → set OPENAI_API_KEY

# 3. Start all services
docker compose up -d

# 4. Run database migrations
docker compose exec backend alembic upgrade head

# 5. Bootstrap a root admin (idempotent — promotes if email exists)
docker compose exec backend python -m app.cli.seed_admin \
    --email admin@example.com --password 'ChangeMe!'

# 6. Seed the 5 official starter templates (used by the /welcome wizard)
docker compose exec backend python -m app.cli.seed_starter_templates \
    --owner-email admin@example.com
```

Open:
- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/api/docs
- **RabbitMQ UI**: http://localhost:15672

### Operational endpoints

| Path | Purpose |
|---|---|
| `GET /healthz` | Liveness — always 200, no deps. Use as k8s `livenessProbe`. |
| `GET /readyz` | Readiness — pings Postgres + Redis. 503 when degraded. |
| `GET /api/openapi.json` | Full OpenAPI spec for client codegen. |

### Operator CLIs

```bash
# Promote an existing user to admin without resetting their password
docker compose exec backend python -m app.cli.seed_admin \
    --email user@example.com --promote-only

# Refresh the seeded starter templates after editing _starter_templates.py
docker compose exec backend python -m app.cli.seed_starter_templates \
    --owner-email admin@example.com
```

For production hardening (JSON logs, Sentry, Stripe Connect payouts) see
[`docs/architecture/operations.md`](docs/architecture/operations.md).

## Development Guide

### Using the CLI

The `forge` CLI manages all services and apps. Available for both Windows and Linux.

```bash
# Linux / Mac / Git Bash
./scripts/forge.sh <command> [target]

# Windows CMD / PowerShell
scripts\forge.cmd <command> [target]
```

### Common Workflows

**Start infrastructure only (recommended for local dev):**

```bash
./scripts/forge.sh start infra        # postgres + redis + rabbitmq
```

**Run backend locally with hot-reload:**

```bash
./scripts/forge.sh install backend    # pip install -e ".[dev]"
./scripts/forge.sh migrate            # alembic upgrade head
./scripts/forge.sh dev backend        # uvicorn --reload on :8000
```

**Run frontend locally:**

```bash
./scripts/forge.sh install frontend   # pnpm install
./scripts/forge.sh dev frontend       # next dev on :3000
```

**Start everything with Docker:**

```bash
./scripts/forge.sh start all          # All services + apps
./scripts/forge.sh status             # Check what's running
./scripts/forge.sh logs backend       # Tail logs
./scripts/forge.sh stop all           # Stop everything
```

### CLI Reference

| Command | Description |
|---|---|
| `start [target]` | Start services via Docker |
| `stop [target]` | Stop services |
| `restart [target]` | Restart services |
| `build [target]` | Build Docker images |
| `dev <target>` | Start local dev server (hot-reload) |
| `logs [target]` | Tail logs |
| `status` | Show running services |
| `health` | Health check endpoints |
| `install <target>` | Install dependencies |
| `test <target>` | Run tests |
| `migrate` | Run database migrations |
| `clean [target]` | Remove containers + volumes |

**Targets:** `all`, `infra`, `apps`, `postgres`, `redis`, `rabbitmq`, `backend`, `frontend`, `docs`

### Manual Setup (without CLI)

**Backend:**

```bash
cd apps/backend
python -m venv .venv
source .venv/bin/activate    # Linux/Mac
# .venv\Scripts\activate     # Windows

pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

**Frontend:**

```bash
cd apps/frontend
pnpm install
pnpm dev
```

**Individual service:**

```bash
cd services/postgres
docker compose up -d         # Start standalone
docker compose logs -f       # Tail logs
docker compose down -v       # Stop + remove data
```

### Environment Variables

**Backend** (`apps/backend/.env`):

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...` | Async DB connection |
| `SECRET_KEY` | `dev-secret-key...` | JWT signing key |
| `OPENAI_API_KEY` | | OpenAI API key |
| `ANTHROPIC_API_KEY` | | Anthropic API key |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed origins |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |

**Frontend** (`apps/frontend/.env.local`):

| Variable | Default | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api` | Backend API URL |
| `NEXT_PUBLIC_WS_URL` | `ws://localhost:8000/api` | WebSocket URL |

### Database Migrations

```bash
# Create new migration
cd apps/backend
alembic revision --autogenerate -m "add new field"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Features

### Agent Builder
- Create agents with system prompt, LLM model selection (OpenAI, Anthropic, Ollama)
- Split-view editor: config on left, live chat preview on right
- Attach tools and knowledge bases per agent

### Custom Tools
- 4 built-in types: HTTP Request, Code Executor, Web Scraper, DB Query
- Dynamic JSON Schema to Pydantic model conversion
- Test tool execution with dry-run endpoint

### Knowledge Base (RAG)
- Upload documents: PDF, DOCX, TXT, MD, CSV, HTML
- Pipeline: parse → chunk (RecursiveCharacterTextSplitter) → embed (OpenAI) → pgvector
- Cosine similarity search, auto-creates retrieval tool for agents

### Visual Workflows
- React Flow drag-and-drop editor with 8 node types
- Compiler: JSON graph → LangGraph StateGraph
- Execution tracking with per-node logs, token usage, latency

### Multi-Agent
- **Supervisor pattern**: coordinator delegates to worker agents
- **Peer collaboration**: sequential processing with synthesis
- Support for mixed LLM providers across agents

### Streaming Chat
- WebSocket with token-by-token streaming
- Tool call indicators (start/end events)
- Markdown rendering, auto-scroll, conversation history

## API Overview

| Group | Endpoints |
|---|---|
| Auth | `POST /api/auth/{register,login,refresh,logout}`, `GET /api/auth/me` |
| Agents | `CRUD /api/agents`, attach/detach tools & KBs |
| Tools | `CRUD /api/tools`, `POST /api/tools/{id}/test` |
| Knowledge | `CRUD /api/knowledge-bases`, upload docs, semantic query |
| Workflows | `CRUD /api/workflows`, execute, run history |
| Conversations | `CRUD /api/conversations`, messages, `WS /api/ws/chat/{id}` |
| Multi-Agent | `POST /api/multi-agent/{supervisor,peer}`, providers list |

Full API docs at http://localhost:8000/api/docs (Swagger UI).

## Documentation

Project specifications live in `docs/` (59 files organized by domain):

```
docs/
├── architecture/    System design, project structure, deployment, dependencies
├── conventions/     Code style rules (backend, frontend, components, database, API)
├── backend/         Per-module specifications
├── frontend/        Per-feature specifications
├── database/        Per-table schema specifications
├── api/             Per-endpoint request/response examples
└── flows/           End-to-end flow specifications
```

An MCP server at `mcp-docs/` provides search tools for AI assistants:

```bash
./scripts/forge.sh dev docs   # Start MCP docs server
```

## License

MIT
