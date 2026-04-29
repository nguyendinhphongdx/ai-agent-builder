# AI Agent Builder (AgentForge)

Open-source AI Agent Builder platform. Monorepo with apps, services, docs, and MCP server.

## Structure

```
apps/backend/     → Python FastAPI + LangChain + LangGraph
apps/frontend/    → Next.js 16 + TypeScript + Tailwind + shadcn/ui (radix-ui primitives)
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
- **shadcn/ui on radix-ui**: components import from `radix-ui` (composed package), not `@base-ui/react`. `asChild` prop works as expected. Prefer `buttonVariants()` for `<Link>` styling so the anchor stays a real `<a>`.
- **Auth**: JWT in httpOnly secure cookies. NOT localStorage.
- **Request context**: `app.context.current_user_id()` reads the authenticated user from a `ContextVar` set by `get_current_user`. New service code should read it directly instead of threading `user_id` through every signature. **Keep explicit in:** login flow (`auth/tokens.py`), workflow runner, ingestion pipeline, webhook background tasks (anything reachable from `asyncio.create_task` outside an HTTP request). For background tasks that *do* need to inherit, wrap with `run_in_request_context(user_id, coro)`.
- **Database**: snake_case plural tables. UUID PKs. JSONB for configs. pgvector for embeddings.

## Running

```bash
docker compose up                          # All services + apps
cd services/postgres && docker compose up  # Standalone postgres
cd apps/backend && uvicorn app.main:app --reload
cd apps/frontend && pnpm dev
```
