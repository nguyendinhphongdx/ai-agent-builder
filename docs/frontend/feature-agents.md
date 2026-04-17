---
id: frontend-feature-agents
title: Agents Feature Module
domain: frontend
tags: [agents, crud, hooks, views, react-query]
related: [frontend-feature-agents-editor, frontend-feature-chat, api-agent-endpoints]
summary: Documents the agents feature types, service layer, React Query hooks, and all views (Library, List, Detail, Create, Editor).
---

# Agents Feature

## Directory: `src/features/agents/`

### Barrel Export (`index.ts`)

Exports: `AgentLibraryView`, `AgentEditorView`, `AgentListView`, `AgentCreateView`, `AgentDetailView`.

## Types (`types/index.ts`)

| Type              | Key Fields                                                                  |
|-------------------|-----------------------------------------------------------------------------|
| `Agent`           | Full agent with `tools: ToolBrief[]`, `knowledge_bases: KnowledgeBaseBrief[]`, `llm_config`, `max_turns`, `is_published`, `status` |
| `AgentListItem`   | Subset: `id`, `name`, `description`, `avatar_url`, `llm_provider`, `llm_model`, `status`, `is_published` |
| `ToolBrief`       | `id`, `name`, `description`, `tool_type`                                   |
| `KnowledgeBaseBrief` | `id`, `name`, `description`, `total_documents`                          |
| `AgentCreateInput`| `name`, `system_prompt` (required); `description`, `llm_provider`, `llm_model`, `llm_config`, `welcome_message`, `max_turns` (optional) |
| `AgentUpdateInput`| Partial of create + `status`, `is_published`                               |

## Service (`services/agentService.ts`)

| Method       | HTTP Call                                      | Returns          |
|--------------|------------------------------------------------|------------------|
| `list`       | `GET /agents`                                  | `AgentListItem[]`|
| `getById`    | `GET /agents/${id}`                            | `Agent`          |
| `create`     | `POST /agents`                                 | `Agent`          |
| `update`     | `PUT /agents/${id}`                            | `Agent`          |
| `delete`     | `DELETE /agents/${id}`                         | void             |
| `attachTool` | `POST /agents/${agentId}/tools/${toolId}`       | void             |
| `detachTool` | `DELETE /agents/${agentId}/tools/${toolId}`      | void             |
| `attachKB`   | `POST /agents/${agentId}/knowledge-bases/${kbId}`| void             |
| `detachKB`   | `DELETE /agents/${agentId}/knowledge-bases/${kbId}`| void           |

## Hooks (`hooks/useAgents.ts`)

### Query Keys

```ts
agentKeys.all    = ["agents"]
agentKeys.list() = ["agents", "list"]
agentKeys.detail(id) = ["agents", "detail", id]
```

| Hook              | Type     | Behavior                                                |
|-------------------|----------|---------------------------------------------------------|
| `useAgents()`     | Query    | Fetches agent list                                      |
| `useAgent(id)`    | Query    | Fetches single agent, `enabled: !!id`                   |
| `useCreateAgent()`| Mutation | Creates agent, invalidates list, navigates to `/agents/${id}` |
| `useUpdateAgent(id)` | Mutation | Updates agent, invalidates detail + list            |
| `useDeleteAgent()`| Mutation | Deletes agent, invalidates list, navigates to `/agents` |

## Views

### AgentLibraryView (`views/AgentLibraryView.tsx`)

The primary agent browsing view at `/libraries`:
- Search bar with text filter
- Status filter pills: all, draft, active, archived
- View mode toggle: grid / list
- Grid shows `AgentGridCard` components; list shows `AgentListRow`
- "New Agent" button links to `/agents/new`
- Empty state with prompt to create first agent

### AgentListView (`views/AgentListView.tsx`)

Simpler list at `/agents` using `AgentCard` component in a 3-column grid.

### AgentDetailView (`views/AgentDetailView.tsx`)

Detail/edit page showing `AgentForm` in a Card with back button, status badge, Chat link, and Delete button.

### AgentCreateView (`views/AgentCreateView.tsx`)

Create page with `AgentForm` in a Card. On submit calls `useCreateAgent()`.

### AgentEditorView (`views/AgentEditorView.tsx`)

See `feature-agents-editor.md` for full documentation.
