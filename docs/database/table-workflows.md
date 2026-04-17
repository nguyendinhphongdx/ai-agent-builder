---
id: table-workflows
title: "Tables: workflows, workflow_nodes, workflow_edges, workflow_runs"
domain: database
tags: [workflows, nodes, edges, execution, schema]
related: [schema-overview, workflows, table-agents]
summary: Four-table workflow system storing versioned DAGs of typed nodes and edges, with execution history including per-node traces and cost tracking.
---

# Workflow Tables

Source: `apps/backend/app/models/workflow.py`, `workflow_node.py`, `workflow_edge.py`, `workflow_run.py`

## Table: workflows

Inherits: `Base`, `UUIDMixin`, `TimestampMixin`

| Column | Type | Nullable | Default | Constraints | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | no | `uuid4()` | PK | |
| `user_id` | `UUID` | no | -- | FK(`users.id`) CASCADE, INDEX | Owner. |
| `agent_id` | `UUID` | yes | `NULL` | FK(`agents.id`) SET NULL, INDEX | Optional linked agent. |
| `name` | `String(255)` | no | -- | -- | Workflow name. |
| `description` | `Text` | yes | `NULL` | -- | |
| `version` | `Integer` | no | `1` | -- | Incremented on each `save_graph` call. |
| `is_active` | `Boolean` | no | `False` | -- | Whether the workflow is enabled. |
| `viewport` | `JSONB` | no | `{}` | -- | Canvas editor viewport state (zoom, pan). |
| `created_at` | `TIMESTAMP(tz)` | no | `now()` | -- | |
| `updated_at` | `TIMESTAMP(tz)` | no | `now()` | -- | |

## Table: workflow_nodes

Inherits: `Base`, `UUIDMixin` (custom `created_at`)

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | no | `uuid4()` | PK |
| `workflow_id` | `UUID` | no | -- | FK(`workflows.id`) CASCADE, INDEX |
| `node_type` | `String(50)` | no | -- | See node_type enum below. |
| `label` | `String(255)` | yes | `NULL` | Display label on canvas. |
| `config` | `JSONB` | no | `{}` | Type-specific configuration. |
| `position_x` | `Float` | no | `0` | Canvas X coordinate. |
| `position_y` | `Float` | no | `0` | Canvas Y coordinate. |
| `width` | `Float` | yes | `NULL` | Node width on canvas. |
| `height` | `Float` | yes | `NULL` | Node height on canvas. |
| `created_at` | `TIMESTAMP(tz)` | no | `now()` | |

### node_type Enum

| Value | Config Fields | Purpose |
|---|---|---|
| `input` | _(none)_ | Workflow entry point. |
| `output` | _(none)_ | Workflow exit, captures final result. |
| `llm` | `llm_provider`, `llm_model`, `system_prompt`, `temperature`, `max_tokens` | LLM invocation. |
| `tool` | `tool_id` | Execute a registered tool. |
| `condition` | `condition_expression`, `branches` | Boolean branch with true/false routing. |
| `human_input` | `prompt_message`, `input_key`, `default_value`, `input_type`, `options` | Pause for user input. |

## Table: workflow_edges

Inherits: `Base`, `UUIDMixin` (custom `created_at`)

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | no | `uuid4()` | PK |
| `workflow_id` | `UUID` | no | -- | FK(`workflows.id`) CASCADE, INDEX |
| `source_node_id` | `UUID` | no | -- | FK(`workflow_nodes.id`) CASCADE, INDEX |
| `target_node_id` | `UUID` | no | -- | FK(`workflow_nodes.id`) CASCADE, INDEX |
| `source_handle` | `String(100)` | yes | `NULL` | Output port (`"true"`, `"false"` for conditions). |
| `target_handle` | `String(100)` | yes | `NULL` | Input port on target node. |
| `label` | `String(255)` | yes | `NULL` | Display label on the edge. |
| `style` | `JSONB` | no | `{}` | CSS styling for canvas rendering. |
| `created_at` | `TIMESTAMP(tz)` | no | `now()` | |

## Table: workflow_runs

Inherits: `Base`, `UUIDMixin` (custom timestamps)

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | no | `uuid4()` | PK |
| `workflow_id` | `UUID` | no | -- | FK(`workflows.id`) CASCADE, INDEX |
| `user_id` | `UUID` | no | -- | FK(`users.id`) CASCADE, INDEX |
| `conversation_id` | `UUID` | yes | `NULL` | FK(`conversations.id`) SET NULL |
| `status` | `String(20)` | no | `"running"` | `"running"` -> `"completed"` / `"failed"`, INDEX |
| `input_data` | `JSONB` | no | -- | Input payload provided at execution time. |
| `output_data` | `JSONB` | yes | `NULL` | Final output from the output node. |
| `error_message` | `Text` | yes | `NULL` | Error details on failure. |
| `node_executions` | `JSONB` | no | `[]` | Per-node execution trace (see below). |
| `total_tokens` | `Integer` | no | `0` | Sum of tokens across all LLM nodes. |
| `total_cost` | `Numeric(10,6)` | no | `0` | Estimated cost in USD. |
| `started_at` | `TIMESTAMP(tz)` | no | `now()` | |
| `completed_at` | `TIMESTAMP(tz)` | yes | `NULL` | |

### node_executions JSONB Structure

```json
[
  {
    "node_id": "uuid-string",
    "node_type": "llm",
    "label": "Summarize",
    "status": "completed",
    "input_data": {"content": "..."},
    "output_data": {"content": "..."},
    "error": null,
    "tokens_used": 450,
    "started_at": "2026-01-15T10:30:00Z",
    "completed_at": "2026-01-15T10:30:02Z"
  }
]
```

## Relationships

- `workflows` 1:N `workflow_nodes` (cascade delete-orphan)
- `workflows` 1:N `workflow_edges` (cascade delete-orphan)
- `workflows` 1:N `workflow_runs` (cascade delete-orphan)
- `workflows` N:1 `agents` (optional, SET NULL on agent delete)
- `workflow_runs` N:1 `conversations` (optional, SET NULL)
