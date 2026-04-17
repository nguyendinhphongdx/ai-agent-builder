---
id: backend-conversations
title: Conversations
domain: backend
tags: [conversations, messages, websocket, streaming, langgraph]
related: [backend-agents, backend-llm-providers, backend-tools, backend-knowledge]
summary: Conversation and Message models, WebSocket chat handler with LangGraph streaming, save_message with counter updates.
---

# Conversations

## Overview

Conversations track multi-turn interactions between a user and an agent. Messages
are persisted with metadata (token usage, latency, tool calls). Real-time chat
uses a WebSocket handler that streams agent responses via LangGraph, forwarding
token, tool_start, and tool_end events to the client.

## Specification

### Conversation Model

Table: `conversations`. Inherits `UUIDMixin` + `TimestampMixin`.

| Column | Type | Default | Description |
|---|---|---|---|
| `user_id` | `UUID` FK -> users | required | Owner |
| `agent_id` | `UUID` FK -> agents | required | Associated agent |
| `title` | `String(255)` | `None` | Optional conversation title |
| `is_pinned` | `Boolean` | `False` | Pin to top of list |
| `is_archived` | `Boolean` | `False` | Hide from default listing |
| `summary` | `Text` | `None` | Auto-generated summary |
| `total_messages` | `Integer` | `0` | Running message count |
| `total_tokens` | `Integer` | `0` | Running token count |
| `metadata` | `JSONB` | `{}` | Extensible metadata |
| `last_message_at` | `TIMESTAMP` | `None` | Timestamp of most recent message |

### Message Model

Table: `messages`. Inherits `UUIDMixin` (no TimestampMixin; has its own `created_at`).

| Column | Type | Default | Description |
|---|---|---|---|
| `conversation_id` | `UUID` FK | required | Parent conversation |
| `parent_message_id` | `UUID` FK -> messages | `None` | For branching/tree structure |
| `role` | `String(20)` | required | `"user"`, `"assistant"`, `"tool"`, `"system"` |
| `content` | `Text` | required | Message text |
| `content_type` | `String(20)` | `"text"` | `"text"`, `"image"`, `"file"` |
| `tool_calls` | `JSONB` | `None` | LLM tool call requests |
| `tool_call_id` | `String(255)` | `None` | ID linking tool response to call |
| `tool_name` | `String(255)` | `None` | Name of executed tool |
| `attachments` | `JSONB` | `[]` | File attachments |
| `token_usage` | `JSONB` | `None` | `{ prompt_tokens, completion_tokens, total_tokens }` |
| `latency_ms` | `Integer` | `None` | LLM response time in milliseconds |
| `llm_model` | `String(100)` | `None` | Model used for this response |
| `feedback` | `String(10)` | `None` | `"up"` or `"down"` from user |
| `created_at` | `TIMESTAMP` | `server_default=now()` | Creation time |

### `save_message` Function

```python
async def save_message(db, conversation_id, role, content, **kwargs) -> Message
```

1. Creates and inserts the `Message` record.
2. Increments `conversation.total_messages` by 1.
3. Sets `conversation.last_message_at` to current UTC time.
4. If `token_usage` is provided in kwargs, adds `total_tokens` to `conversation.total_tokens`.
5. Flushes and refreshes the message.

### WebSocket Handler (`chat_websocket`)

```python
async def chat_websocket(ws, conversation_id, user_id, db)
```

**Connection lifecycle:**

1. Accept WebSocket connection.
2. Validate conversation exists and belongs to user.
3. Validate associated agent exists.
4. Enter receive loop.

**Message loop (per user message):**

1. Receive JSON: `{ "content": "user text" }`.
2. Save user message via `save_message` and commit.
3. Load last 50 messages as conversation history.
4. Stream agent response via `execute_agent_stream(agent, history, db)`.
5. Forward events to client as JSON.
6. Save full assistant response via `save_message` with `llm_model` and `latency_ms`.
7. Send `{ "type": "done" }` to signal completion.

### Streaming Protocol

Events sent over WebSocket as JSON objects:

| `type` | Additional Fields | Description |
|---|---|---|
| `token` | `content: str` | Incremental text token from LLM |
| `tool_start` | `name: str`, `input: str` | Tool invocation started (input truncated to 500 chars) |
| `tool_end` | `name: str`, `result: str` | Tool completed (result truncated to 500 chars) |
| `done` | -- | Stream finished |
| `error` | `message: str` | Error occurred |

### Agent Execution (`execute_agent_stream`)

- Builds LLM via `build_llm_from_agent(agent)`.
- Builds tools via `build_agent_tools(agent, db)` which includes custom tools and
  an auto-generated `search_knowledge_base` tool if the agent has knowledge bases.
- Converts DB messages to LangChain message objects via `_build_history`.
- If tools exist: creates a LangGraph ReAct agent (`create_react_agent`) and
  streams via `astream_events(version="v2")`.
- If no tools: streams directly from `llm.astream`.

### REST Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/conversations` | List conversations (filter by `agent_id` query param) |
| `POST` | `/api/conversations` | Create conversation |
| `GET` | `/api/conversations/{conv_id}` | Get conversation detail |
| `GET` | `/api/conversations/{conv_id}/messages` | Get messages (paginated: `limit`, `offset`) |

Listing excludes archived conversations (`is_archived == False`), ordered by
`last_message_at DESC NULLS LAST`.

## File Structure

```
apps/backend/app/conversations/
  __init__.py
  router.py          # REST endpoints
  schemas.py         # Conversation/Message create/response schemas
  service.py         # CRUD + save_message
  ws.py              # WebSocket handler
apps/backend/app/agents/
  executor.py        # execute_agent_stream, build_agent_tools, AgentStreamEvent
apps/backend/app/models/
  conversation.py    # Conversation ORM model
  message.py         # Message ORM model
```

## Key Functions / Classes

| Symbol | File | Purpose |
|---|---|---|
| `chat_websocket` | `ws.py` | WebSocket connection handler |
| `save_message` | `service.py` | Insert message + update counters |
| `get_messages` | `service.py` | Paginated message query (ASC order) |
| `list_conversations` | `service.py` | Filtered, sorted conversation list |
| `execute_agent_stream` | `executor.py` | LangGraph streaming execution |
| `AgentStreamEvent` | `executor.py` | Event wrapper with `to_dict()` |

## Examples

```javascript
// Client-side WebSocket usage
const ws = new WebSocket(`ws://host/api/conversations/${convId}/chat`);
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === "token") appendText(data.content);
  if (data.type === "tool_start") showToolSpinner(data.name);
  if (data.type === "done") finalize();
};
ws.send(JSON.stringify({ content: "Hello!" }));
```

### Constraints

- The WebSocket handler MUST validate conversation and agent ownership before processing.
- History loaded for agent execution is limited to the last 50 messages.
- Assistant responses MUST be saved with `llm_model` and `latency_ms`.
- `save_message` MUST atomically update conversation counters.
- Message pagination defaults to `limit=100` (max 200), `offset=0`.
