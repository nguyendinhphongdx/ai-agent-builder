---
id: frontend-feature-agents-editor
title: Agent Editor Split-View Layout
domain: frontend
tags: [agents, editor, split-view, knowledge, tools, multi-agent, preview-chat]
related: [frontend-feature-agents, frontend-feature-chat, frontend-websocket-client]
summary: Documents the AgentEditorView split layout and its sub-components -- KnowledgeUploadSection, ToolsSelector, MultiAgentSection, and AgentPreviewChat.
---

# Agent Editor View

## File: `src/features/agents/views/AgentEditorView.tsx`

### Dual Mode

Accepts optional `agentId` prop. When present, loads existing agent data and enters edit mode. When absent, operates in create mode.

### Split Layout

```
+---------------------------+---------------------------+
|     Left Panel (50%)      |    Right Panel (50%)      |
|    Configuration Form     |   AgentPreviewChat        |
+---------------------------+---------------------------+
```

### Left Panel -- Configuration

Top bar with back link to `/libraries`, title ("Edit Agent" or "New Agent"), and Save/Create button.

Scrollable form area contains (in order):

1. **Name** -- text input
2. **Description** -- text input
3. **Provider/Model** -- two select dropdowns side by side
   - Providers: OpenAI, Anthropic
   - Models: GPT-4o, GPT-4o Mini, Claude Sonnet 4, Claude Haiku 4.5
4. **Instructions** -- textarea (monospace font, system prompt)
5. **Welcome Message** -- text input
6. **Knowledge Base** -- `KnowledgeUploadSection`
7. **Tools** -- `ToolsSelector`
8. **Multi-Agent** -- `MultiAgentSection`

Zod validation: `name` and `system_prompt` required; `llm_provider` and `llm_model` required.

## KnowledgeUploadSection

**File:** `src/features/agents/components/KnowledgeUploadSection.tsx`

- Drag-and-drop zone with click-to-browse fallback
- Accepted file types: `.pdf`, `.txt`, `.md`, `.docx`, `.csv`, `.html`
- Tracks upload state per file: `uploading` -> `processing` -> `ready` or `failed`
- Shows progress bar during upload, spinner during processing
- Status icons: CheckCircle (ready), AlertCircle (failed), Loader (in progress)
- Remove button per file
- Currently simulates upload/processing (real API integration pending)

## ToolsSelector

**File:** `src/features/agents/components/ToolsSelector.tsx`

- Displays system tools and custom tools as toggleable list items
- System tools (built-in):
  - **Web Search** (globe icon) -- "Search the web for real-time information"
  - **Code Interpreter** (code icon) -- "Execute Python code in a sandbox"
  - **Web Scraper** (globe icon) -- "Extract content from web pages"
- Each tool shows name, description, "System" badge, and checkbox indicator
- Selected tools highlighted with cyan accent (`border-cyan-500/30`, `bg-cyan-500/8`)
- "Manage tools" link to `/tools` page

## MultiAgentSection

**File:** `src/features/agents/components/MultiAgentSection.tsx`

- Three collaboration mode buttons: **Single** (standalone), **Supervisor** (delegates), **Peer** (equal)
- When mode is not "none", shows worker/peer agent picker
- Filters out current agent from available agents
- Selected agents displayed with name, model, and remove button
- "Add Agent" button opens inline dropdown of available agents

## AgentPreviewChat

**File:** `src/features/agents/components/AgentPreviewChat.tsx`

The right panel live chat preview:

1. Creates a conversation via `chatService.createConversation(agentId)` when agentId is available
2. Connects WebSocket via `createChatWS()` when conversation is ready
3. Shows welcome state when no messages ("Test your agent here")
4. Disabled input when no agentId ("Save agent to enable preview")
5. Displays messages with user/assistant avatars
6. Streams assistant responses with `StreamMarkdown` rendering
7. Shows active tool indicator during tool execution
8. Bouncing dots animation while waiting for first token
9. Auto-scrolls to bottom on new messages/stream content
10. Enter to send, Shift+Enter for newline
