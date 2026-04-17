---
id: table-tools
title: "Table: tools"
domain: database
tags: [tools, api, function, schema]
related: [schema-overview, table-agents, agent-executor, workflows]
summary: Custom tool definitions with type-specific JSONB config and JSON Schema input/output declarations.
---

# Table: tools

Source: `apps/backend/app/models/tool.py`

Inherits: `Base`, `UUIDMixin`, `TimestampMixin`

## Columns

| Column | Type | Nullable | Default | Constraints | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | no | `uuid4()` | PK | |
| `user_id` | `UUID` | no | -- | FK(`users.id`) CASCADE, INDEX | Owning user. |
| `name` | `String(255)` | no | -- | -- | Tool display name (also used as the LangChain tool name). |
| `description` | `Text` | no | -- | -- | Human-readable description passed to the LLM for tool selection. |
| `tool_type` | `String(50)` | no | -- | INDEX | Discriminator for config structure. |
| `config` | `JSONB` | no | -- | -- | Type-specific configuration (see below). |
| `input_schema` | `JSONB` | no | -- | -- | JSON Schema defining expected input parameters. |
| `output_schema` | `JSONB` | yes | `NULL` | -- | JSON Schema defining the return value structure. |
| `is_active` | `Boolean` | no | `True` | -- | Inactive tools are excluded from agent execution. |
| `timeout_seconds` | `Integer` | no | `30` | -- | Maximum execution time before timeout. |
| `created_at` | `TIMESTAMP(tz)` | no | `now()` | -- | From TimestampMixin. |
| `updated_at` | `TIMESTAMP(tz)` | no | `now()` | -- | From TimestampMixin. |

## tool_type Enum

| Value | Description |
|---|---|
| `"api"` | HTTP API call (REST endpoint). |
| `"function"` | Server-side Python function execution. |

## config JSONB Examples

### Type: `"api"`

```json
{
  "url": "https://api.example.com/search",
  "method": "GET",
  "headers": {
    "Authorization": "Bearer {{api_key}}",
    "Content-Type": "application/json"
  },
  "query_params": ["q", "limit"],
  "body_template": null
}
```

### Type: `"function"`

```json
{
  "function_name": "calculate_compound_interest",
  "module_path": "app.tools.builtins.finance",
  "allowed_imports": ["math", "decimal"]
}
```

## input_schema Example

Standard JSON Schema used by LangChain to generate the tool's argument parser:

```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "Search query text"
    },
    "limit": {
      "type": "integer",
      "description": "Maximum results to return",
      "default": 10
    }
  },
  "required": ["query"]
}
```

## Relationships

| Relationship | Target | Type | Notes |
|---|---|---|---|
| `user` | `User` | N:1 | Back-populates `user.tools`. |

Tools are linked to agents through the `agent_tools` junction table (see `table-agents`).

## Indexes

- `user_id` -- filter tools by owner.
- `tool_type` -- filter by tool category.

## Runtime Behavior

The `tool_registry.build(tool_def)` function reads `tool_type` and `config` to construct a LangChain `StructuredTool`. The `input_schema` is used to define the tool's argument schema, while `description` is passed as the tool description for LLM function-calling.
