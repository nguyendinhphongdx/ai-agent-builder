---
id: table-users
title: "Table: users"
domain: database
tags: [users, authentication, schema]
related: [schema-overview, table-agents, table-tools, table-api-keys]
summary: User account table with authentication fields and one-to-many ownership relationships to all major resources.
---

# Table: users

Source: `apps/backend/app/models/user.py`

Inherits: `Base`, `UUIDMixin`, `TimestampMixin`

## Columns

| Column | Type | Nullable | Default | Constraints | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | no | `uuid4()` | PK | From UUIDMixin. |
| `email` | `String(255)` | no | -- | UNIQUE, INDEX | User email address, used for authentication. |
| `hashed_password` | `String(255)` | no | -- | -- | Bcrypt or similar password hash. |
| `full_name` | `String(255)` | yes | `NULL` | -- | Display name. |
| `avatar_url` | `String(512)` | yes | `NULL` | -- | URL to user avatar image. |
| `is_active` | `Boolean` | no | `True` | -- | Account active flag; disabled accounts cannot authenticate. |
| `last_login_at` | `TIMESTAMP(tz)` | yes | `NULL` | -- | Timestamp of most recent login. |
| `created_at` | `TIMESTAMP(tz)` | no | `now()` | -- | From TimestampMixin. |
| `updated_at` | `TIMESTAMP(tz)` | no | `now()` | -- | From TimestampMixin, auto-updates on change. |

## Relationships

All relationships use `cascade="all, delete-orphan"`, meaning deleting a user removes all owned resources.

| Relationship | Target | Type | Back-populates |
|---|---|---|---|
| `agents` | `Agent` | 1:N | `agent.user` |
| `tools` | `Tool` | 1:N | `tool.user` |
| `knowledge_bases` | `KnowledgeBase` | 1:N | `knowledge_base.user` |
| `conversations` | `Conversation` | 1:N | `conversation.user` |
| `api_keys` | `ApiKey` | 1:N | `api_key.user` |

## Indexes

- `email` -- unique index for login lookups.

## Notes

- The `hashed_password` column stores a one-way hash; plaintext passwords are never persisted.
- `is_active` serves as a soft-disable mechanism. Rows are not deleted on account deactivation.
- `last_login_at` is updated on each successful authentication event.
- The user model is the root owner of the entire resource tree. Cascade delete propagates to agents, tools, knowledge bases, conversations, and API keys.
