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

Every feature module has exactly 4 files:

```
app/{module}/
├── __init__.py
├── router.py       # FastAPI endpoints (APIRouter)
├── service.py      # Business logic (pure functions, DB queries)
├── schemas.py      # Pydantic request/response models
└── (optional)      # Extra files per module needs (executor.py, registry.py, etc.)
```

### Rules
1. **router.py** - Only HTTP concerns. Delegates to service. Never contains DB queries directly
2. **service.py** - Pure async functions. Receives `db: AsyncSession` as first arg. Returns ORM models
3. **schemas.py** - Pydantic BaseModel classes. `model_config = {"from_attributes": True}` for ORM mapping
4. **models/** - Centralized in `app/models/`, not per-module

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
