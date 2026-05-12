---
id: api-conversation-endpoints
title: Conversation API Endpoints
domain: api
tags: [conversations, messages, pagination, chat]
related: [frontend-feature-chat, api-websocket-protocol]
summary: Documents Conversation CRUD and message listing with pagination, including request/response examples.
---

# Conversation API Endpoints

**Router:** `app/modules/runtime/chat/conversations/router.py`  
**Prefix:** `/api/conversations`  
**Auth:** All endpoints require `get_current_user`.

## GET /conversations

List conversations for the current user. Optionally filter by agent.

**Query Parameters:**
| Param     | Type    | Default | Description              |
|-----------|---------|---------|--------------------------|
| `agent_id`| UUID?   | null    | Filter by agent ID       |

**Response (200):**
```json
[
  {
    "id": "uuid", "agent_id": "uuid", "title": "Support chat",
    "is_pinned": false, "is_archived": false,
    "total_messages": 12, "total_tokens": 3400,
    "last_message_at": "2026-01-01T12:00:00Z",
    "created_at": "2026-01-01T11:00:00Z"
  }
]
```

## POST /conversations

Create a new conversation with an agent.

**Request:**
```json
{ "agent_id": "uuid", "title": "My chat session" }
```

`title` is optional.

**Response (201):** `ConversationResponse`

## GET /conversations/{conv_id}

Get conversation detail.

**Response (200):** `ConversationResponse`

**Errors:** 404 if conversation not found or not owned by user.

## GET /conversations/{conv_id}/messages

Get messages in a conversation with pagination.

**Query Parameters:**
| Param    | Type | Default | Constraint | Description          |
|----------|------|---------|------------|----------------------|
| `limit`  | int  | 100     | max 200    | Messages per page    |
| `offset` | int  | 0       | min 0      | Skip first N messages|

**Response (200):**
```json
[
  {
    "id": "uuid", "conversation_id": "uuid",
    "role": "user", "content": "How do I reset my password?",
    "content_type": "text", "tool_calls": null, "tool_name": null,
    "token_usage": null, "latency_ms": null, "llm_model": null,
    "feedback": null, "created_at": "2026-01-01T12:00:00Z"
  },
  {
    "id": "uuid", "conversation_id": "uuid",
    "role": "assistant", "content": "To reset your password...",
    "content_type": "text", "tool_calls": null, "tool_name": null,
    "token_usage": {"prompt_tokens": 150, "completion_tokens": 80, "total_tokens": 230},
    "latency_ms": 1200, "llm_model": "gpt-4o",
    "feedback": null, "created_at": "2026-01-01T12:00:01Z"
  }
]
```

## Ownership Verification

All operations verify conversation ownership via `get_conversation(db, conv_id, current_user.id)`. The messages endpoint also checks ownership before returning messages. Returns 404 for conversations not owned by the requesting user.
