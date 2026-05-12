---
id: api-websocket-protocol
title: WebSocket Chat Protocol
domain: api
tags: [websocket, streaming, chat, protocol, real-time, langgraph]
related: [frontend-websocket-client, frontend-feature-chat, api-conversation-endpoints]
summary: Documents the full WebSocket protocol for chat streaming in both directions -- client-to-server messages and server-to-client events.
---

# WebSocket Chat Protocol

## Connection

**URL:** `ws://{host}/api/ws/chat/{conversation_id}`

**Backend handler:** `app/modules/runtime/chat/conversations/ws.py` -> `chat_websocket()`

### Handshake

1. Client opens WebSocket to the conversation URL
2. Server accepts the connection
3. Server validates:
   - Conversation exists and belongs to the user
   - Associated agent exists
4. On validation failure, sends `error` message and closes connection

## Client-to-Server Messages

Single message format:

```json
{ "content": "User message text" }
```

- Empty `content` is silently ignored
- Client should only send when WebSocket is in OPEN state

## Server-to-Client Messages

Five message types form a discriminated union on `type`:

### token

Streaming text chunk from the LLM.

```json
{ "type": "token", "content": "partial text..." }
```

Emitted on `on_chat_model_stream` events from LangGraph. Only emitted when chunk has non-empty `content`.

### tool_start

A tool has started executing.

```json
{ "type": "tool_start", "name": "search_knowledge_base", "input": "{\"query\": \"...\"}" }
```

Input is truncated to 500 characters.

### tool_end

A tool has finished executing.

```json
{ "type": "tool_end", "name": "search_knowledge_base", "result": "Found 3 relevant passages..." }
```

Result is truncated to 500 characters.

### done

The response is complete. All tokens have been sent.

```json
{ "type": "done" }
```

### error

An error occurred during processing.

```json
{ "type": "error", "message": "Error description" }
```

## Message Sequence

Typical flow for a single user message:

```
Client -> Server: { "content": "How do I reset my password?" }

Server -> Client: { "type": "tool_start", "name": "search_knowledge_base" }
Server -> Client: { "type": "tool_end", "name": "search_knowledge_base", "result": "..." }
Server -> Client: { "type": "token", "content": "To " }
Server -> Client: { "type": "token", "content": "reset " }
Server -> Client: { "type": "token", "content": "your password..." }
Server -> Client: { "type": "done" }
```

Tool events may appear before, during, or between token streams depending on the LangGraph execution flow.

## Backend Processing

For each user message:

1. Saves user message to DB via `save_message()`
2. Commits transaction
3. Loads conversation history (last 50 messages)
4. Calls `execute_agent_stream()` which:
   - Builds LLM from agent config
   - Builds tools (custom tools + KB retrieval tool)
   - Constructs LangChain message history with system prompt
   - If tools exist: uses `create_react_agent()` from LangGraph and streams via `astream_events(v2)`
   - If no tools: streams directly via `llm.astream()`
5. Accumulates full response text
6. Saves assistant message to DB with `llm_model` and `latency_ms`
7. Sends `done` event

## Connection Lifecycle

- Connection persists for multiple message exchanges (long-lived)
- Server handles `WebSocketDisconnect` gracefully (silent pass)
- Client should close connection when leaving the chat view
- No heartbeat/ping mechanism in current implementation

## Frontend Integration

The frontend `createChatWS()` function maps server events to callbacks:

| Server Event  | Frontend Callback  |
|---------------|-------------------|
| `token`       | `onToken(content)` |
| `tool_start`  | `onToolStart(name)`|
| `tool_end`    | `onToolEnd(name, result)` |
| `done`        | `onDone()`        |
| `error`       | `onError(message)` |
