---
id: flows-chat-with-agent
title: Chat with Agent Flow
domain: flows
tags: [chat, websocket, streaming, tool-calls, conversations]
related: [api-websocket-protocol, frontend-feature-chat, frontend-websocket-client]
summary: End-to-end flow from creating a conversation through WebSocket connection, sending a message, streaming response with tool calls, to message persistence.
---

# Chat with Agent Flow

## Overview

User enters the chat view for an agent, a conversation is created, a WebSocket connection is established, and messages stream in real-time with tool call indicators.

## Step-by-Step

### 1. Enter Chat View

User clicks "Chat" on an agent -> navigates to `/agents/{id}/chat` -> renders `ChatView`.

### 2. Create Conversation

`ChatView` mounts and calls:

```
POST /api/conversations { agent_id: agentId }
```

Backend creates a Conversation record. Frontend receives `conversationId` and sets state.

### 3. Connect WebSocket

Once `conversationId` is available, `useChat(conversationId)` hook:

1. Fetches existing messages via `GET /api/conversations/{id}/messages` (empty for new conversation)
2. Creates WebSocket: `createChatWS({ conversationId, onToken, onToolStart, onToolEnd, onDone, onError })`
3. Connection URL: `ws://host/api/ws/chat/{conversationId}`

### 4. Server Validates Connection

Backend `chat_websocket()`:

1. Accepts WebSocket connection
2. Validates conversation exists and belongs to user
3. Validates associated agent exists
4. Enters message loop

### 5. User Sends Message

Frontend `sendMessage(content)`:

1. Creates local user `Message` object and adds to store
2. Sets `isStreaming: true`
3. Sends `{ content }` JSON via WebSocket

### 6. Backend Processes Message

Server receives message and:

1. Saves user message to DB: `save_message(db, conversation_id, role="user", content=...)`
2. Commits transaction
3. Loads last 50 messages as conversation history
4. Calls `execute_agent_stream(agent, history, db)`

### 7. Agent Execution

`execute_agent_stream()`:

1. Builds LLM from agent config (provider + model)
2. Builds tools: custom tools via `tool_registry.build_many()` + KB retrieval tool if knowledge bases attached
3. Constructs message history with system prompt
4. **With tools:** Creates LangGraph ReAct agent, streams via `astream_events(v2)`
5. **Without tools:** Streams directly via `llm.astream()`

### 8. Stream Response

Events streamed to client:

| Event | Trigger | Data |
|-------|---------|------|
| `tool_start` | `on_tool_start` LangGraph event | Tool name, truncated input |
| `tool_end` | `on_tool_end` LangGraph event | Tool name, truncated result |
| `token` | `on_chat_model_stream` event | Text chunk |
| `done` | After all events complete | (none) |

### 9. Frontend Renders Stream

Zustand store updates drive UI:

- `token` -> `appendStreamContent(chunk)` -> `StreamMarkdown` re-renders
- `tool_start` -> `setActiveTool(name)` -> shows "Using {name}..." indicator
- `tool_end` -> `setActiveTool(null)` -> hides indicator
- `done` -> creates final `Message` object from accumulated content, adds to store, resets stream state

### 10. Persist Assistant Response

Backend after streaming completes:

1. Saves assistant message with `full_response`, `llm_model`, and `latency_ms`
2. Commits to DB

### 11. Auto-Scroll

`ChatWindow` scrolls to bottom on every `messages` or `streamingContent` change via `useEffect` + `scrollIntoView({ behavior: "smooth" })`.

## Error Handling

- WebSocket errors: `onError` callback logs and resets stream state
- Backend exceptions during execution: sent as `{ type: "error", message }` to client
- Disconnect: server catches `WebSocketDisconnect` silently
