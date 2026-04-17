---
id: schema-overview
title: Database Schema Overview
domain: database
tags: [schema, postgresql, er-diagram, models]
related: [table-users, table-agents, table-tools, table-knowledge, table-conversations, table-workflows, table-api-keys]
summary: Overview of all 16 database tables, their relationships, shared mixins, and naming conventions.
---

# Database Schema Overview

Source: `apps/backend/app/models/__init__.py`, `apps/backend/app/db/base.py`

## Table Inventory

The schema contains 16 tables across five domains:

| Domain | Tables |
|---|---|
| Identity | `users`, `api_keys` |
| Agents | `agents`, `agent_tools`, `agent_knowledge_bases` |
| Tools | `tools` |
| Knowledge | `knowledge_bases`, `documents`, `document_chunks` |
| Conversations | `conversations`, `messages` |
| Workflows | `workflows`, `workflow_nodes`, `workflow_edges`, `workflow_runs` |

## ER Diagram

```
users 1──N agents
users 1──N tools
users 1──N knowledge_bases
users 1──N conversations
users 1──N api_keys

agents N──N tools           (via agent_tools)
agents N──N knowledge_bases (via agent_knowledge_bases)
agents 1──N conversations
agents 1──N workflows

conversations 1──N messages
messages  ?──?  messages    (parent_message_id self-ref)

knowledge_bases 1──N documents
documents       1──N document_chunks
document_chunks N──1 knowledge_bases  (denormalized FK)

workflows 1──N workflow_nodes
workflows 1──N workflow_edges
workflows 1──N workflow_runs
workflow_nodes <── workflow_edges (source + target FKs)
workflow_runs  N──1 conversations (optional)
```

## Shared Mixins

### `Base` (DeclarativeBase)

All models inherit from this SQLAlchemy declarative base.

### `UUIDMixin`

Adds `id: UUID` as the primary key with `uuid4` default generation.

### `TimestampMixin`

Adds `created_at` and `updated_at` as `TIMESTAMP(timezone=True)` columns. `created_at` defaults to `now()`; `updated_at` uses `onupdate=func.now()`.

## Naming Conventions

- **Table names**: lowercase plural (`users`, `agents`, `workflow_nodes`).
- **Junction tables**: `{parent}_{child}` pattern (`agent_tools`, `agent_knowledge_bases`).
- **Foreign keys**: `{referenced_table_singular}_id` (e.g., `user_id`, `agent_id`).
- **Status columns**: `String(20)` with documented state machine values.
- **JSONB columns**: used for flexible/polymorphic data (`config`, `metadata`, `tool_calls`, `llm_config`).

## Primary Key Strategy

All tables use UUID v4 primary keys. Junction tables (`agent_tools`, `agent_knowledge_bases`) use composite primary keys from both foreign key columns.

## Cascade Behavior

- **Owner relationships** (user -> agents, etc.): `CASCADE` on delete, removing all owned resources.
- **Optional references** (workflow -> agent, workflow_run -> conversation): `SET NULL` on delete.
- **Junction tables**: `CASCADE` on both sides.
- **Message self-reference**: `SET NULL` on parent deletion, preserving child messages.

## Extensions Required

- **pgvector**: The `document_chunks.embedding` column uses `Vector(1536)` from the pgvector extension.
