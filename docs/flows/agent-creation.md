---
id: flows-agent-creation
title: Agent Creation Flow
domain: flows
tags: [agents, creation, editor, tools, knowledge-base, preview]
related: [frontend-feature-agents-editor, api-agent-endpoints, frontend-feature-chat]
summary: End-to-end flow from creating an agent through configuring LLM, attaching tools and knowledge bases, to testing via the preview chat.
---

# Agent Creation Flow

## Overview

User creates a new agent via the split-view editor, configures its LLM, attaches tools and knowledge bases, and tests it with live chat preview.

## Step-by-Step

### 1. Navigate to Editor

User clicks "New Agent" from Libraries view -> navigates to `/agents/new` -> renders `AgentEditorView` without `agentId` (create mode).

### 2. Configure Agent

Left panel form fields:

1. **Name** (required): e.g., "Customer Support Bot"
2. **Description** (optional): brief summary
3. **Provider**: OpenAI or Anthropic (default: OpenAI)
4. **Model**: GPT-4o, GPT-4o Mini, Claude Sonnet 4, Claude Haiku 4.5 (default: GPT-4o)
5. **Instructions**: System prompt (default: "You are a helpful AI assistant.")
6. **Welcome Message** (optional): initial greeting

### 3. Save Agent

User clicks "Create" button:

1. Zod validates form: `name` and `system_prompt` required
2. `useCreateAgent().mutate(data)` calls `POST /api/agents`
3. Backend creates agent record with `status: "draft"`
4. On success, invalidates agent list cache and navigates to `/agents/${agent.id}`

### 4. Agent Editor Loads in Edit Mode

Now at `/agents/{id}`, `AgentEditorView` receives `agentId`:

1. `useAgent(id)` fetches full agent detail
2. Form is populated with existing values via `form.reset()`
3. Right panel preview chat becomes available

### 5. Attach Tools

In the Tools section:
1. User toggles system tools (Web Search, Code Interpreter, Web Scraper) or custom tools
2. Currently managed via local state `selectedTools[]`
3. Persist via `agentService.attachTool(agentId, toolId)` -> `POST /api/agents/{id}/tools/{toolId}`

### 6. Upload Knowledge Base

In the Knowledge Base section:
1. User drags/drops files or clicks to browse
2. Accepted: PDF, TXT, MD, DOCX, CSV, HTML
3. Upload progress tracked per file
4. Processing status: uploading -> processing (chunks + embeddings) -> ready
5. Backend: `POST /api/knowledge-bases/{id}/documents` triggers ingestion pipeline

### 7. Configure Multi-Agent (Optional)

In the Multi-Agent section:
1. User selects mode: Single (default), Supervisor, or Peer
2. If Supervisor/Peer: adds other agents as workers/peers
3. Collaboration config stored for later multi-agent execution

### 8. Test via Preview Chat

Right panel `AgentPreviewChat`:
1. Creates a conversation: `POST /api/conversations` with `agent_id`
2. Opens WebSocket: `ws://host/api/ws/chat/{conversationId}`
3. User sends test message -> streamed response appears
4. Tool calls shown with indicators (name + spinner)
5. Markdown rendered via `StreamMarkdown`

### 9. Iterate

User can modify any config, click "Save", and immediately test changes in the preview. The `useUpdateAgent` mutation saves without navigation.
