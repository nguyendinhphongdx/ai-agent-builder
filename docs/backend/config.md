---
id: backend-config
title: Application Configuration
domain: backend
tags: [config, settings, env, pydantic]
related: [backend-database, backend-auth, backend-llm-providers]
summary: Settings class using pydantic-settings, all environment variables, defaults, and .env file loading.
---

# Application Configuration

## Overview

All backend configuration is centralized in a single `Settings` class built on
`pydantic-settings`. Values are read from environment variables first, then from
a `.env` file in the project root. The module exports a singleton `settings`
instance used throughout the application.

## Specification

### Settings class

| Field | Type | Env Var | Default | Description |
|---|---|---|---|---|
| `APP_NAME` | `str` | `APP_NAME` | `"AI Agent Builder"` | Display name of the application. |
| `DEBUG` | `bool` | `DEBUG` | `False` | Enables SQL echo logging and other debug behaviour. |
| `API_PREFIX` | `str` | `API_PREFIX` | `"/api"` | URL prefix for all API routes. |
| `DATABASE_URL` | `str` | `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/lc_agent` | Async database connection string (asyncpg driver). |
| `DATABASE_URL_SYNC` | `str` | `DATABASE_URL_SYNC` | `postgresql://postgres:postgres@localhost:5432/lc_agent` | Sync database connection string (used by Alembic). |
| `SECRET_KEY` | `str` | `SECRET_KEY` | `"change-me-in-production-use-a-long-random-string"` | HMAC key for signing JWT tokens. **Must be changed in production.** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `int` | `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Lifetime of access tokens in minutes. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `int` | `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Lifetime of refresh tokens in days. |
| `ALGORITHM` | `str` | `ALGORITHM` | `"HS256"` | JWT signing algorithm. |
| `OPENAI_API_KEY` | `str` | `OPENAI_API_KEY` | `""` | API key for OpenAI provider. |
| `ANTHROPIC_API_KEY` | `str` | `ANTHROPIC_API_KEY` | `""` | API key for Anthropic provider. |
| `UPLOAD_DIR` | `str` | `UPLOAD_DIR` | `"uploads"` | Local directory for uploaded files. |
| `CORS_ORIGINS` | `list[str]` | `CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed CORS origins. |

### Loading behaviour

- Uses `SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")`.
- Environment variables take precedence over `.env` file values.
- Unknown variables in `.env` are silently ignored (`extra="ignore"`).

## File Structure

```
apps/backend/app/
  config.py          # Settings class + singleton
```

## Key Functions / Classes

### `Settings(BaseSettings)`

Pydantic settings model. Inherits validation, type coercion, and `.env` parsing
from `pydantic-settings`.

### `settings`

Module-level singleton. Import with:

```python
from app.platform.config import settings
```

## Examples

```python
# Reading a value
from app.platform.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
```

```bash
# .env file
SECRET_KEY=my-super-secret-key-here
DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/mydb
OPENAI_API_KEY=sk-...
DEBUG=true
```

### Constraints

- `SECRET_KEY` MUST be a cryptographically random string in production (minimum 32 characters recommended).
- `DATABASE_URL` MUST use the `postgresql+asyncpg` driver scheme.
- `DATABASE_URL_SYNC` MUST use the plain `postgresql` driver scheme.
- `CORS_ORIGINS` accepts a JSON-encoded list when set via environment variable.
