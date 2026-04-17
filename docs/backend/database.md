---
id: backend-database
title: Database Layer
domain: backend
tags: [database, sqlalchemy, asyncpg, session, mixins]
related: [backend-config]
summary: SQLAlchemy async setup with DeclarativeBase, UUID and Timestamp mixins, async session factory, and get_db dependency.
---

# Database Layer

## Overview

The database layer provides async PostgreSQL connectivity via SQLAlchemy 2.0 and
asyncpg. It defines a `DeclarativeBase`, reusable column mixins, an async session
factory, and a FastAPI dependency that manages transaction lifecycle per request.

## Specification

### Base class

`Base` is the `DeclarativeBase` from which every ORM model inherits. It carries
no columns of its own.

### Mixins

#### `UUIDMixin`

Adds a single column:

| Column | Type | Constraints | Default |
|---|---|---|---|
| `id` | `UUID` (PostgreSQL native) | Primary key | `uuid.uuid4()` (client-side) |

#### `TimestampMixin`

Adds two columns:

| Column | Type | Constraints | Default |
|---|---|---|---|
| `created_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | `server_default=func.now()` |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | `server_default=func.now()`, `onupdate=func.now()` |

Models that need both mixins inherit as `class MyModel(Base, UUIDMixin, TimestampMixin)`.

### Async Engine

```python
engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
```

- Driver: `asyncpg` (connection string starts with `postgresql+asyncpg://`).
- SQL logging is enabled when `settings.DEBUG` is `True`.

### Async Session Factory

```python
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
```

- `expire_on_commit=False` keeps loaded attributes accessible after commit without
  an extra query, which is important for returning data in API responses.

### `get_db` dependency

```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
```

- Yields an `AsyncSession` scoped to the request.
- Auto-commits on success.
- Rolls back on any exception, then re-raises.
- Used as a FastAPI `Depends()` on every endpoint that needs DB access.

## File Structure

```
apps/backend/app/db/
  __init__.py
  base.py            # Base, UUIDMixin, TimestampMixin
  session.py          # engine, async_session_factory, get_db
```

## Key Functions / Classes

| Symbol | Location | Purpose |
|---|---|---|
| `Base` | `base.py` | SQLAlchemy `DeclarativeBase` |
| `UUIDMixin` | `base.py` | Adds UUID primary key |
| `TimestampMixin` | `base.py` | Adds `created_at` / `updated_at` |
| `engine` | `session.py` | Global async engine |
| `async_session_factory` | `session.py` | Session maker bound to engine |
| `get_db()` | `session.py` | FastAPI dependency yielding a session |

## Examples

```python
from app.db.session import get_db
from app.db.base import Base, UUIDMixin, TimestampMixin

# Defining a model
class Widget(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "widgets"
    name: Mapped[str] = mapped_column(String(255))

# Using the dependency
@router.get("/widgets")
async def list_widgets(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Widget))
    return result.scalars().all()
```

### Constraints

- All models MUST inherit from `Base`.
- Models that represent user-facing entities MUST use both `UUIDMixin` and `TimestampMixin`.
- Never create a raw `AsyncSession` outside of `get_db`; always use the dependency.
- Do not call `session.commit()` manually inside service functions; `get_db` handles it.
