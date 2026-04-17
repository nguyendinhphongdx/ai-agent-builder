---
id: frontend-feature-chat
title: Chat Feature Module
domain: frontend
tags: [chat, websocket, zustand, streaming, conversations, messages]
related: [frontend-websocket-client, frontend-feature-chat-components, api-websocket-protocol]
summary: Documents the chat feature types, service, Zustand store (chatStore), useChat hook, and WebSocket integration for real-time streaming.
---

# Chat Feature

## Directory: `src/features/chat/`

## Types (`types/index.ts`)

### Conversation

| Field            | Type      | Description                      |
|------------------|-----------|----------------------------------|
| `id`             | `string`  | UUID                             |
| `agent_id`       | `string`  | Associated agent                 |
| `title`          | `string?` | Optional conversation title      |
| `is_pinned`      | `boolean` | Whether pinned by user           |
| `is_archived`    | `boolean` | Whether archived                 |
| `total_messages` | `number`  | Message count                    |
| `total_tokens`   | `number`  | Token usage                      |
| `last_message_at`| `string?` | Timestamp of last message        |
| `created_at`     | `string`  | Creation timestamp               |

### Message

| Field            | Type      | Description                                 |
|------------------|-----------|---------------------------------------------|
| `role`           | enum      | `"user"`, `"assistant"`, `"system"`, `"tool"` |
| `content`        | `string`  | Message text                                |
| `content_type`   | `string`  | Content format identifier                   |
| `tool_calls`     | `unknown?`| Tool call data if present                   |
| `tool_name`      | `string?` | Name of tool used                           |
| `token_usage`    | object?   | `{ prompt_tokens, completion_tokens, total_tokens }` |
| `latency_ms`     | `number?` | Response latency                            |
| `llm_model`      | `string?` | Model used for generation                   |
| `feedback`       | `string?` | User feedback (thumbs up/down)              |

## Service (`services/chatService.ts`)

| Method               | HTTP Call                        | Returns          |
|----------------------|----------------------------------|------------------|
| `listConversations`  | `GET /conversations?agent_id=`   | `Conversation[]` |
| `createConversation` | `POST /conversations`            | `Conversation`   |
| `getMessages`        | `GET /conversations/${id}/messages` | `Message[]`   |

## Zustand Store (`stores/chatStore.ts`)

Global state for the active chat session using Zustand:

### State

| Field              | Type       | Description                    |
|--------------------|------------|--------------------------------|
| `messages`         | `Message[]`| Full message history           |
| `isStreaming`      | `boolean`  | Whether currently streaming    |
| `streamingContent` | `string`   | Accumulated stream text        |
| `activeToolName`   | `string?`  | Tool currently executing       |

### Actions

| Action                | Description                              |
|-----------------------|------------------------------------------|
| `setMessages(msgs)`   | Replace all messages                     |
| `addMessage(msg)`     | Append single message                    |
| `setStreaming(bool)`   | Set streaming flag                       |
| `appendStreamContent` | Append chunk to `streamingContent`       |
| `setActiveTool(name)` | Set active tool indicator                |
| `resetStream()`       | Clear stream content, streaming, and tool|

## useChat Hook (`hooks/useChat.ts`)

Orchestrates conversation data loading and WebSocket communication.

### Setup Flow

1. Loads existing messages via `useQuery` with key `["messages", conversationId]`
2. Sets loaded messages into Zustand store via `useEffect`
3. Creates WebSocket connection via `createChatWS()` with conversation ID

### WebSocket Event Handling

| Event       | Store Action                                          |
|-------------|-------------------------------------------------------|
| `token`     | `appendStreamContent(content)`                        |
| `tool_start`| `setActiveTool(name)`                                 |
| `tool_end`  | `setActiveTool(null)`                                 |
| `done`      | Reads `streamingContent` from store, creates assistant Message, calls `addMessage`, then `resetStream` |
| `error`     | Logs error, calls `resetStream`                       |

### sendMessage(content)

1. Guard: returns if no WS ref, already streaming, or empty content
2. Creates local `Message` object with `role: "user"`
3. Calls `addMessage` and `setStreaming(true)`
4. Sends content via `wsRef.current.send(content)`

### Return Value

```ts
{ messages, isStreaming, streamingContent, activeToolName, sendMessage }
```
