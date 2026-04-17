---
id: table-conversations
title: "Tables: conversations, messages"
domain: database
tags: [conversations, messages, tool-calls, tokens, schema]
related: [schema-overview, table-agents, table-users, agent-executor]
summary: Conversation and message tables supporting chat history, message branching, tool call logging, token tracking, and user feedback.
---

# Conversation & Message Tables

Source: `apps/backend/app/models/conversation.py`, `message.py`

## Table: conversations

Inherits: `Base`, `UUIDMixin`, `TimestampMixin`

| Column | Type | Nullable | Default | Constraints | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | no | `uuid4()` | PK | |
| `user_id` | `UUID` | no | -- | FK(`users.id`) CASCADE | Owning user. |
| `agent_id` | `UUID` | no | -- | FK(`agents.id`) CASCADE, INDEX | Agent this conversation belongs to. |
| `title` | `String(255)` | yes | `NULL` | -- | Conversation title (user-set or auto-generated). |
| `is_pinned` | `Boolean` | no | `False` | -- | Pin to top of conversation list. |
| `is_archived` | `Boolean` | no | `False` | INDEX | Hide from default list view. |
| `summary` | `Text` | yes | `NULL` | -- | Auto-generated conversation summary. |
| `total_messages` | `Integer` | no | `0` | -- | Counter cache for message count. |
| `total_tokens` | `Integer` | no | `0` | -- | Accumulated token usage across all messages. |
| `metadata` | `JSONB` | no | `{}` | -- | Arbitrary metadata. |
| `last_message_at` | `TIMESTAMP(tz)` | yes | `NULL` | -- | Timestamp of most recent message. |
| `created_at` | `TIMESTAMP(tz)` | no | `now()` | -- | From TimestampMixin. |
| `updated_at` | `TIMESTAMP(tz)` | no | `now()` | -- | From TimestampMixin. |

## Table: messages

Inherits: `Base`, `UUIDMixin` (custom `created_at`, no `updated_at`)

| Column | Type | Nullable | Default | Constraints | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | no | `uuid4()` | PK | |
| `conversation_id` | `UUID` | no | -- | FK(`conversations.id`) CASCADE | Parent conversation. |
| `parent_message_id` | `UUID` | yes | `NULL` | FK(`messages.id`) SET NULL | Self-referencing FK for message branching. |
| `role` | `String(20)` | no | -- | -- | `"user"`, `"assistant"`, `"tool"`, `"system"`. |
| `content` | `Text` | no | -- | -- | Message text content. |
| `content_type` | `String(20)` | no | `"text"` | -- | `"text"`, `"image"`, `"file"`. |
| `tool_calls` | `JSONB` | yes | `NULL` | -- | Tool calls requested by the LLM (see below). |
| `tool_call_id` | `String(255)` | yes | `NULL` | -- | ID linking a `role="tool"` message to its call. |
| `tool_name` | `String(255)` | yes | `NULL` | -- | Name of the executed tool. |
| `attachments` | `JSONB` | no | `[]` | -- | List of file attachments. |
| `token_usage` | `JSONB` | yes | `NULL` | -- | Per-message token breakdown (see below). |
| `latency_ms` | `Integer` | yes | `NULL` | -- | LLM response time in milliseconds. |
| `llm_model` | `String(100)` | yes | `NULL` | -- | Model that generated this message. |
| `feedback` | `String(10)` | yes | `NULL` | -- | User rating: `"up"` or `"down"`. |
| `created_at` | `TIMESTAMP(tz)` | no | `now()` | -- | |

## tool_calls JSONB Structure

Stored on `role="assistant"` messages when the LLM requests tool invocations:

```json
[
  {
    "id": "call_abc123",
    "type": "function",
    "function": {
      "name": "search_knowledge_base",
      "arguments": "{\"query\": \"revenue Q3\"}"
    }
  }
]
```

## token_usage JSONB Structure

```json
{
  "prompt_tokens": 1200,
  "completion_tokens": 350,
  "total_tokens": 1550
}
```

## attachments JSONB Structure

```json
[
  {
    "filename": "report.pdf",
    "url": "/uploads/conv/abc123/report.pdf",
    "mime_type": "application/pdf",
    "size": 204800
  }
]
```

## Message Branching

The `parent_message_id` column enables a tree structure for conversation branching (e.g., regenerating an assistant response creates a sibling rather than replacing the original). `SET NULL` on delete preserves child messages if a parent is removed.

## Relationships

- `conversations` 1:N `messages` (cascade delete-orphan)
- `conversations` N:1 `users`, N:1 `agents`
- `messages` self-referencing via `parent_message_id`
