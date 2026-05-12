---
id: backend-agents
title: Agents
domain: backend
tags: [agents, llm, crud, tools, knowledge-base]
related: [backend-tools, backend-knowledge, backend-llm-providers, backend-conversations]
summary: Agent model with LLM config, CRUD operations, and attach/detach for tools and knowledge bases via junction tables.
---

# Agents

## Overview

An Agent is the core entity representing an AI assistant. It binds together an LLM
configuration, a system prompt, a set of tools, and a set of knowledge bases. Agents
are owned by a user and serve as the target for conversations.

## Specification

### Agent Model

Table: `agents`. Inherits `UUIDMixin` + `TimestampMixin`.

| Column | Type | Default | Description |
|---|---|---|---|
| `user_id` | `UUID` FK -> users | required | Owner |
| `name` | `String(255)` | required | Display name |
| `description` | `Text` | `None` | Optional description |
| `avatar_url` | `String(512)` | `None` | Avatar image URL |
| `system_prompt` | `Text` | required | System message defining agent behaviour |
| `llm_provider` | `String(50)` | `"openai"` | `"openai"`, `"anthropic"`, or `"ollama"` |
| `llm_model` | `String(100)` | `"gpt-4o"` | Model identifier |
| `llm_config` | `JSONB` | `{}` | Extra LLM parameters (see below) |
| `welcome_message` | `Text` | `None` | Greeting shown at conversation start |
| `max_turns` | `Integer` | `50` | Maximum exchange turns per conversation |
| `is_published` | `Boolean` | `False` | Whether agent is publicly visible |
| `status` | `String(20)` | `"draft"` | `"draft"` or `"active"` |

### `llm_config` JSONB Structure

```json
{
  "temperature": 0.7,
  "max_tokens": 4096,
  "base_url": null
}
```

All fields are optional. Consumed by `build_llm_from_agent()` in the LLM provider module.

### Junction Tables

**`agent_tools`** (N-N between agents and tools):

| Column | Type | Notes |
|---|---|---|
| `agent_id` | UUID PK, FK -> agents | CASCADE delete |
| `tool_id` | UUID PK, FK -> tools | CASCADE delete |
| `priority` | Integer | Default `0` |
| `added_at` | TIMESTAMP | `server_default=now()` |

**`agent_knowledge_bases`** (N-N between agents and knowledge bases):

| Column | Type | Notes |
|---|---|---|
| `agent_id` | UUID PK, FK -> agents | CASCADE delete |
| `knowledge_base_id` | UUID PK, FK -> knowledge_bases | CASCADE delete |
| `added_at` | TIMESTAMP | `server_default=now()` |

### Relationships

- `tools` -- loaded via `selectinload` (lazy="selectin").
- `knowledge_bases` -- loaded via `selectinload`.
- `conversations` -- cascade `all, delete-orphan` (deleting an agent deletes its conversations).

### CRUD Operations

| Operation | Function | Notes |
|---|---|---|
| List | `list_agents(db, user_id)` | Ordered by `updated_at DESC` |
| Get | `get_agent(db, agent_id, user_id)` | Eager-loads tools + KBs |
| Create | `create_agent(db, user_id, **kwargs)` | Flushes and refreshes relations |
| Update | `update_agent(db, agent, **kwargs)` | Skips `None` values |
| Delete | `delete_agent(db, agent)` | Cascades to conversations |

### Attach / Detach

| Function | Description |
|---|---|
| `attach_tool(db, agent_id, tool_id)` | Inserts into `agent_tools` |
| `detach_tool(db, agent_id, tool_id)` | Deletes from `agent_tools`; no-op if missing |
| `attach_knowledge_base(db, agent_id, kb_id)` | Inserts into `agent_knowledge_bases` |
| `detach_knowledge_base(db, agent_id, kb_id)` | Deletes from `agent_knowledge_bases`; no-op if missing |

### API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/agents` | List user's agents |
| `POST` | `/api/agents` | Create agent |
| `GET` | `/api/agents/{agent_id}` | Get agent detail with tools and KBs |
| `PUT` | `/api/agents/{agent_id}` | Update agent |
| `DELETE` | `/api/agents/{agent_id}` | Delete agent |
| `POST` | `/api/agents/{agent_id}/tools/{tool_id}` | Attach tool |
| `DELETE` | `/api/agents/{agent_id}/tools/{tool_id}` | Detach tool |
| `POST` | `/api/agents/{agent_id}/knowledge-bases/{kb_id}` | Attach KB |
| `DELETE` | `/api/agents/{agent_id}/knowledge-bases/{kb_id}` | Detach KB |

All endpoints require authentication via `get_current_user`.

## File Structure

```
apps/backend/app/modules/studio/agents/
  __init__.py
  executor.py        # LangGraph agent execution (see conversations doc)
  router.py          # FastAPI endpoints
  schemas.py         # AgentCreate, AgentUpdate, AgentResponse, etc.
  service.py         # CRUD + attach/detach functions
  orchestration/     # supervisor + peer multi-agent (see multi-agent doc)
apps/backend/app/models/
  agent.py           # Agent, AgentTool, AgentKnowledgeBase ORM models
```

## Key Functions / Classes

| Symbol | File | Purpose |
|---|---|---|
| `Agent` | `models/agent.py` | ORM model |
| `AgentTool` | `models/agent.py` | Junction table model |
| `AgentKnowledgeBase` | `models/agent.py` | Junction table model |
| `list_agents` | `service.py` | Query all agents for a user |
| `get_agent` | `service.py` | Single agent with relations |
| `create_agent` | `service.py` | Insert + refresh |
| `update_agent` | `service.py` | Partial update |
| `attach_tool` / `detach_tool` | `service.py` | Manage tool links |

## Examples

```python
# Creating an agent
agent = await create_agent(
    db, user_id,
    name="Support Bot",
    system_prompt="You are a helpful support agent.",
    llm_provider="anthropic",
    llm_model="claude-sonnet-4-20250514",
    llm_config={"temperature": 0.5, "max_tokens": 2048},
)
```

### Constraints

- `user_id` MUST match the authenticated user; agents are tenant-scoped.
- `llm_provider` MUST be one of `"openai"`, `"anthropic"`, `"ollama"`.
- `status` MUST be `"draft"` or `"active"`.
- Deleting an agent MUST cascade-delete all associated conversations.
