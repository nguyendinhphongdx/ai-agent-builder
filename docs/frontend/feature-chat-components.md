---
id: frontend-feature-chat-components
title: Chat UI Components
domain: frontend
tags: [chat, components, markdown, streaming, auto-scroll, ui]
related: [frontend-feature-chat, frontend-websocket-client]
summary: Documents ChatWindow, MessageBubble, ChatInput, and StreamMarkdown components including auto-scroll behavior and streaming display logic.
---

# Chat UI Components

## ChatView (`views/ChatView.tsx`)

Entry point for the `/agents/[id]/chat` route.

1. Loads agent data via `useAgent(agentId)`
2. Creates a new conversation via `chatService.createConversation(agentId)` on mount
3. Renders a header with back link to agent detail and agent name
4. Renders `ChatWindow` once `conversationId` is available, or "Connecting..." placeholder

Layout: full viewport height minus header (`h-[calc(100vh-3.5rem)]`).

## ChatWindow (`components/ChatWindow.tsx`)

Main chat container that integrates the `useChat` hook.

### Structure

```
<ScrollArea> (flex-1, padded)
  <MessageBubble /> for each message
  {streaming indicator when active}
  <div ref={bottomRef} />  <!-- scroll anchor -->
</ScrollArea>
<ChatInput />
```

### Auto-Scroll

Uses a `bottomRef` div at the end of the message list. Scrolls into view with `behavior: "smooth"` whenever `messages` or `streamingContent` change via `useEffect`.

### Streaming Indicator

When `isStreaming` is true, shows:
- Bot avatar icon
- Active tool name with spinner if `activeToolName` is set ("Using {name}...")
- `streamingContent` text if available (plain text, whitespace-preserved)
- Three bouncing dots if no content and no active tool (waiting for first token)

Max width constrained to 80% of container (`max-w-[80%]`).

## MessageBubble (`components/MessageBubble.tsx`)

Renders a single message with role-appropriate styling.

| Role       | Layout        | Avatar               | Bubble Color              |
|------------|---------------|----------------------|---------------------------|
| `user`     | `flex-row-reverse` | Primary bg, User icon | `bg-primary text-primary-foreground` |
| `assistant`| `flex-row`    | Muted bg, Bot icon   | `bg-muted text-foreground`|

Content is rendered as `whitespace-pre-wrap` plain text. Max width 80%.

## ChatInput (`components/ChatInput.tsx`)

Textarea-based input with send button.

- Auto-resizing textarea: `min-h-[44px]`, `max-h-[120px]`, `resize-none`
- **Enter** submits (calls `onSend` with trimmed value, clears input, refocuses)
- **Shift+Enter** inserts newline
- Send button disabled when `disabled` prop is true or input is empty
- `disabled` prop set to `true` during streaming

## StreamMarkdown (`components/StreamMarkdown.tsx`)

Renders markdown content using `react-markdown` with `remark-gfm` plugin.

Prose styling (dark theme optimized):
- Text: `text-white/75` with relaxed leading
- Headings: `text-white`
- Strong: `text-white`
- Code inline: `text-cyan-300`, `bg-white/8`, rounded
- Code blocks: `bg-white/6` with `border-white/8` border
- Links: `text-cyan-400`, no underline, underline on hover
- List items: `text-white/70`
- Blockquotes: `border-white/15`, `text-white/50`

Used in `AgentPreviewChat` for streaming and completed assistant messages. The `ChatWindow` component uses plain text rendering instead.
