---
id: conventions-database
title: Database Conventions - Naming, Types, Indexes
domain: conventions
tags: [conventions, database, postgresql, naming, uuid, jsonb, indexes, soft-delete, timestamps]
related: [database-schema-overview, conventions-backend]
summary: "snake_case plural table names. UUID v4 PKs. JSONB for flexible configs. TimestampMixin for created_at/updated_at. Soft delete via status/is_archived."
---

# Database Conventions

## Naming
- Tables: `snake_case`, **plural** (`users`, `workflow_nodes`)
- Columns: `snake_case` (`created_at`, `knowledge_base_id`)
- Foreign keys: `{referenced_table_singular}_id` (`user_id`, `agent_id`)
- Junction tables: `{table1}_{table2}` (`agent_tools`, `agent_knowledge_bases`)
- Indexes: auto-named by SQLAlchemy

## Primary Keys
- ALL tables use `UUID v4` as primary key
- Generated server-side via `uuid.uuid4()` (Python) or `gen_random_uuid()` (SQL)
- Column type: `UUID(as_uuid=True)`

## Mixins

```python
class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
```

## JSONB Fields
- Used for flexible, type-varying data (tool config, LLM config, node config)
- Validation at **application layer** via Pydantic, NOT database constraints
- Always have a default: `default=dict` or `default=list`

## Soft Delete vs Hard Delete
| Strategy | Tables |
|---|---|
| Hard delete (CASCADE) | tools, documents, document_chunks, workflow_nodes, workflow_edges |
| Soft delete (status/flag) | users (`is_active`), agents (`status: archived`), conversations (`is_archived`) |

## Index Strategy
- Foreign keys: always indexed
- Status/filter columns: indexed (`status`, `is_archived`, `tool_type`)
- Unique constraints: `users.email`
- Vector index: `IVFFLAT(embedding vector_cosine_ops) WITH (lists = 100)`
- Composite: `messages(conversation_id, created_at)`

## Denormalized Counters
`knowledge_bases.total_documents`, `knowledge_bases.total_chunks`, `conversations.total_messages` — updated by application logic after insert/delete.
