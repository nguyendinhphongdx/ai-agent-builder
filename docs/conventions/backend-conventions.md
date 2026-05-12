---
id: conventions-backend
title: Backend Conventions - Python Code Style & Module Pattern
domain: conventions
tags: [conventions, backend, python, fastapi, module-pattern, router, service, schema, naming]
related: [arch-project-structure, conventions-database, conventions-api]
summary: "Backend uses 4-layer module pattern: router.py (endpoints) → service.py (business logic) → models/ (ORM) → schemas.py (Pydantic). Python 3.12, async everywhere, type hints required."
---

# Backend Conventions

## Module Pattern (MUST follow)

Feature modules live under `app/modules/<bucket>/<feature>/` (see
[arch-project-structure](../architecture/project-structure.md) for the 7-bucket
taxonomy: `studio`, `runtime`, `identity`, `integrations`, `commerce`, `ops`,
`api`). Every feature module has exactly 4 files:

```
app/modules/<bucket>/<feature>/
├── __init__.py
├── router.py       # FastAPI endpoints (APIRouter)
├── service.py      # Business logic (pure functions, DB queries)
├── schemas.py      # Pydantic request/response models
└── (optional)      # Extra files per module needs (executor.py, registry.py, etc.)
```

Examples: `app/modules/studio/agents/`, `app/modules/runtime/chat/conversations/`,
`app/modules/identity/auth/`, `app/modules/commerce/payments/checkout/`.

### Rules
1. **router.py** - Only HTTP concerns. Delegates to service. Never contains DB queries directly
2. **service.py** - Pure async functions. Reads the caller from `app.platform.context.current_user_id()` (and `current_workspace_id()`); does **not** thread `user_id` through every signature. Returns ORM models
3. **schemas.py** - Pydantic BaseModel classes. `model_config = {"from_attributes": True}` for ORM mapping
4. **models/** - Centralized in `app/models/` (flat — alembic depends on this), not per-module
5. **Engines vs modules** - Heavy non-HTTP code (workflow runner, retrieval, ingestion) lives in `app/core/`, not in the feature module. Modules call into core engines.
6. **Background loops** - Async loops with `start()/stop()` live in `app/background/`, not inside the module that owns the data they operate on.
7. **Infra** - Cross-cutting concerns (config, db, security, storage, observability, permissions, rate_limit, CLI) live under `app/platform/`. Import as `app.platform.config`, `app.platform.db.session`, etc.

## Naming

| What | Convention | Example |
|---|---|---|
| Files | snake_case | `workflow_node.py` |
| Classes | PascalCase | `WorkflowNode` |
| Functions | snake_case | `create_agent()` |
| Routes | kebab-case | `/knowledge-bases/{id}` |
| DB tables | snake_case, plural | `workflow_nodes` |
| Pydantic schemas | PascalCase + suffix | `AgentCreate`, `AgentResponse`, `AgentUpdate` |

## Async

- ALL database operations are async (`await db.execute(...)`)
- ALL service functions are `async def`
- Use `AsyncSession` from `sqlalchemy.ext.asyncio`
- Use `asyncpg` driver (not psycopg2)

## Dependencies

```python
# Standard pattern for protected endpoints
@router.get("")
async def list_items(
    current_user: User = Depends(get_current_user),  # Auth
    db: AsyncSession = Depends(get_db),                # DB session
):
```

## Error Handling

```python
# Use HTTPException with standard status codes
raise HTTPException(status_code=404, detail="Agent not found")
raise HTTPException(status_code=409, detail="Email already registered")
```

## Imports Order (ruff enforced)
1. Standard library
2. Third-party
3. Local (`app.`)
