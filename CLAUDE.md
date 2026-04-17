# AI Agent Builder (AgentForge)

Open-source AI Agent Builder platform. Monorepo with apps, services, docs, and MCP server.

## Structure

```
apps/backend/     → Python FastAPI + LangChain + LangGraph
apps/frontend/    → Next.js 16 + TypeScript + Tailwind + shadcn/ui (@base-ui)
services/         → postgres (pgvector), redis, rabbitmq (each has own docker-compose)
docs/             → Source of truth specifications (62 files)
mcp-docs/         → Node.js MCP server for doc search
```

## MCP Documentation Server

This project has an MCP server at `mcp-docs/` registered in `.mcp.json`. Use it to search project docs:
- `search_docs("query")` - keyword search across all docs
- `get_doc("doc-id")` - get full doc content
- `list_docs("domain")` - list docs (architecture, conventions, backend, frontend, database, api, flows)
- `get_schema("table_name")` - get DB table schema
- `get_api("/api/endpoint")` - get API endpoint docs
- `get_component("name")` - get frontend feature docs

## Critical Conventions (read `docs/conventions/` for details)

- **Backend**: 4-layer module pattern (router → service → model → schema). Async everywhere.
- **Frontend**: Feature-based arch. Thin App Router. TanStack Query for server state. Zustand UI-only.
- **No `asChild`**: shadcn uses @base-ui/react. Use `buttonVariants()` for links, `render` prop for triggers.
- **Auth**: JWT in httpOnly secure cookies. NOT localStorage.
- **Database**: snake_case plural tables. UUID PKs. JSONB for configs. pgvector for embeddings.

## Running

```bash
docker compose up                          # All services + apps
cd services/postgres && docker compose up  # Standalone postgres
cd apps/backend && uvicorn app.main:app --reload
cd apps/frontend && pnpm dev
```
