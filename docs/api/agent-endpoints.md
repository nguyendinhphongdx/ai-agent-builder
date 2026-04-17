---
id: api-agent-endpoints
title: Agent API Endpoints
domain: api
tags: [agents, crud, tools, knowledge-bases, attach, detach]
related: [frontend-feature-agents, api-tool-endpoints, api-knowledge-endpoints]
summary: Documents all Agent CRUD endpoints plus tool and knowledge base attach/detach operations with request/response examples.
---

# Agent API Endpoints

**Router:** `app/agents/router.py`  
**Prefix:** `/api/agents`  
**Auth:** All endpoints require `get_current_user` dependency.

## GET /agents

List all agents owned by the current user.

**Response (200):**
```json
[
  {
    "id": "uuid", "name": "Support Bot", "description": "Handles support",
    "avatar_url": null, "llm_provider": "openai", "llm_model": "gpt-4o",
    "status": "active", "is_published": true, "created_at": "2026-01-01T00:00:00Z"
  }
]
```

## POST /agents

Create a new agent.

**Request:**
```json
{
  "name": "Support Bot",
  "description": "Handles customer support",
  "system_prompt": "You are a helpful support agent.",
  "llm_provider": "openai",
  "llm_model": "gpt-4o",
  "welcome_message": "How can I help?"
}
```

**Response (201):** Full `AgentResponse` with `tools[]` and `knowledge_bases[]` (initially empty).

## GET /agents/{agent_id}

Get full agent detail including attached tools and knowledge bases.

**Response (200):** `AgentResponse` with nested `tools` and `knowledge_bases` arrays.

**Errors:** 404 if agent not found or not owned by user.

## PUT /agents/{agent_id}

Update agent fields. Only provided fields are updated (`exclude_unset=True`).

**Request:** Partial `AgentUpdate` -- any subset of agent fields.

**Response (200):** Updated `AgentResponse`.

## DELETE /agents/{agent_id}

Delete an agent.

**Response:** 204 No Content.

## POST /agents/{agent_id}/tools/{tool_id}

Attach a tool to an agent.

**Response (201):**
```json
{ "message": "Tool attached" }
```

**Errors:** 404 if agent not found.

## DELETE /agents/{agent_id}/tools/{tool_id}

Detach a tool from an agent.

**Response:** 204 No Content.

## POST /agents/{agent_id}/knowledge-bases/{kb_id}

Attach a knowledge base to an agent.

**Response (201):**
```json
{ "message": "Knowledge base attached" }
```

## DELETE /agents/{agent_id}/knowledge-bases/{kb_id}

Detach a knowledge base from an agent.

**Response:** 204 No Content.

## Ownership Model

All operations verify that the agent belongs to the current user via `get_agent(db, agent_id, current_user.id)`. Returns 404 rather than 403 for agents owned by other users (prevents enumeration).
