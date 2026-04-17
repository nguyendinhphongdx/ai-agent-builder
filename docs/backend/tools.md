---
id: backend-tools
title: Tools
domain: backend
tags: [tools, registry, builder, langchain, structured-tool]
related: [backend-agents, backend-config]
summary: Tool model, ToolRegistry with builder pattern, four built-in builders (HTTP, CodeExec, WebScrape, DBQuery), JSON Schema to Pydantic conversion, and CRUD endpoints.
---

# Tools

## Overview

Tools are user-defined capabilities that agents can invoke at runtime. Each tool
is persisted in the database with a `tool_type`, a `config` JSONB payload, and a
JSON Schema for inputs. At execution time the `ToolRegistry` selects the correct
`ToolBuilder`, converts the definition into a LangChain `StructuredTool`, and
dynamically generates a Pydantic input model from the JSON Schema.

## Specification

### Tool Model

Table: `tools`. Inherits `UUIDMixin` + `TimestampMixin`.

| Column | Type | Default | Description |
|---|---|---|---|
| `user_id` | `UUID` FK -> users | required | Owner |
| `name` | `String(255)` | required | Display name |
| `description` | `Text` | required | Description shown to LLM for tool selection |
| `tool_type` | `String(50)` | required | One of: `http_request`, `code_exec`, `web_scrape`, `db_query` |
| `config` | `JSONB` | required | Type-specific configuration (see below) |
| `input_schema` | `JSONB` | required | JSON Schema describing tool input parameters |
| `output_schema` | `JSONB` | `None` | Optional JSON Schema for output |
| `is_active` | `Boolean` | `True` | Inactive tools are skipped by `build_many` |
| `timeout_seconds` | `Integer` | `30` | Execution timeout |

### `tool_type` Enum Values

`http_request` | `code_exec` | `web_scrape` | `db_query`

### Config JSONB Per Type

**`http_request`:**
```json
{
  "url": "https://api.example.com/users/{user_id}",
  "method": "GET",
  "headers": { "Authorization": "Bearer ..." },
  "body_template": "{\"name\": \"{name}\"}"
}
```
Placeholders `{key}` in `url` and `body_template` are replaced with input kwargs.

**`code_exec`:**
```json
{
  "code_template": "print('Hello {name}')"
}
```
Writes template to a temp `.py` file and executes via `subprocess.run`. Output truncated to 4000 chars.

**`web_scrape`:**
```json
{
  "url_template": "https://example.com/{path}",
  "max_length": 5000
}
```
GETs the URL via httpx and returns raw text truncated to `max_length`.

**`db_query`:**
```json
{
  "connection_string": "postgresql://...",
  "max_rows": 50
}
```
Executes a user-provided SELECT query via `asyncpg`. Security: only `SELECT`
statements are allowed; blocked keywords include `insert`, `update`, `delete`,
`drop`, `alter`, `create`, `truncate`, `grant`, `revoke`.

### `input_schema` Format

Standard JSON Schema. Example:
```json
{
  "properties": {
    "query": { "type": "string", "description": "SQL query to execute" }
  },
  "required": ["query"]
}
```

### `json_schema_to_pydantic(schema) -> type[BaseModel]`

Converts a JSON Schema dict to a runtime Pydantic model using `create_model`.
Type mapping: `string->str`, `integer->int`, `number->float`, `boolean->bool`,
`array->list`, `object->dict`. Fields not in `required` default to `None` with
an optional union type.

### ToolRegistry

Singleton `tool_registry` in `registry.py`.

| Method | Description |
|---|---|
| `register_builder(tool_type, builder)` | Register a custom builder |
| `build(tool_def) -> StructuredTool` | Build a single tool |
| `build_many(tool_defs) -> list[StructuredTool]` | Build all active tools |

Built-in builders registered at init: `http_request`, `code_exec`, `web_scrape`, `db_query`.

### Builder Pattern

All builders extend `ToolBuilder` and implement `build(tool_def) -> StructuredTool`.
Each builder creates an async `execute(**kwargs)` closure, generates an `args_schema`
via `json_schema_to_pydantic`, and returns `StructuredTool.from_function(...)`.

Tool names are normalized: `tool_def.name.replace(" ", "_").lower()`.

### API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/tools` | List user's tools |
| `POST` | `/api/tools` | Create tool |
| `GET` | `/api/tools/{tool_id}` | Get tool detail |
| `PUT` | `/api/tools/{tool_id}` | Update tool |
| `DELETE` | `/api/tools/{tool_id}` | Delete tool |
| `POST` | `/api/tools/{tool_id}/test` | Test tool execution with sample input |

The test endpoint builds the tool, invokes it with `input_data`, and returns
`{ success, result, error, latency_ms }`.

## File Structure

```
apps/backend/app/tools/
  __init__.py
  builtins/           # Reserved for future built-in tool modules
  registry.py         # ToolRegistry, builders, json_schema_to_pydantic
  router.py           # FastAPI endpoints
  schemas.py          # ToolCreate, ToolUpdate, ToolResponse, ToolTestRequest/Response
  service.py          # CRUD functions
apps/backend/app/models/
  tool.py             # Tool ORM model
```

## Key Functions / Classes

| Symbol | File | Purpose |
|---|---|---|
| `ToolRegistry` | `registry.py` | Singleton that maps tool_type to builder |
| `ToolBuilder` | `registry.py` | Abstract base for builders |
| `HTTPRequestToolBuilder` | `registry.py` | HTTP request execution |
| `CodeExecToolBuilder` | `registry.py` | Python code execution |
| `WebScrapeToolBuilder` | `registry.py` | Web page scraping |
| `DBQueryToolBuilder` | `registry.py` | Read-only database queries |
| `json_schema_to_pydantic` | `registry.py` | Runtime Pydantic model generation |
| `tool_registry` | `registry.py` | Global singleton instance |

## Examples

```python
from app.tools.registry import tool_registry

# Build a single tool from DB record
lc_tool = tool_registry.build(tool_record)
result = await lc_tool.ainvoke({"query": "SELECT count(*) FROM users"})
```

### Constraints

- `tool_type` MUST be one of the four registered types or a custom-registered type.
- `input_schema` MUST be a valid JSON Schema with a `properties` key.
- `db_query` tools MUST only allow SELECT statements; the blocked-keyword check is mandatory.
- `code_exec` executes arbitrary Python; use only in trusted environments.
- HTTP output is truncated to 4000 characters; web scrape to `max_length` (default 5000).
