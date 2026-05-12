---
id: api-multi-agent-endpoints
title: Multi-Agent API Endpoints
domain: api
tags: [multi-agent, supervisor, peer, collaboration, langgraph]
related: [frontend-feature-agents-editor, flows-multi-agent-collaboration]
summary: Documents the supervisor and peer collaboration endpoints and the providers listing endpoint with request/response examples.
---

# Multi-Agent API Endpoints

**Router:** `app/modules/studio/agents/orchestration/router.py`  
**Prefix:** `/api/multi-agent`  
**Auth:** Supervisor and peer endpoints require `get_current_user`.

## POST /multi-agent/supervisor

Run the supervisor orchestration pattern. The first agent in `agent_ids` acts as supervisor; the rest are workers.

**Request:**
```json
{
  "message": "Research and summarize recent AI developments",
  "agent_ids": ["supervisor-uuid", "researcher-uuid", "writer-uuid"],
  "max_iterations": 10
}
```

**Validation:** Requires at least 2 agents (1 supervisor + 1 worker).

**Response (200):**
```json
{
  "response": "Here is the synthesized summary of recent AI developments...",
  "agent_outputs": {
    "Researcher": "Found 5 key developments...",
    "Writer": "Drafted summary covering..."
  },
  "pattern": "supervisor",
  "iterations": 3
}
```

### Supervisor Flow

1. Supervisor LLM decides which worker to route to (responds with `ROUTE: worker_name`)
2. Selected worker executes with its own tools and system prompt
3. Worker result is fed back to supervisor
4. Supervisor decides next action: route to another worker or `ROUTE: FINISH`
5. Loop continues until FINISH or `max_iterations` reached
6. Final supervisor message becomes the response

## POST /multi-agent/peer

Run the peer collaboration pattern. Agents process sequentially, each receiving the outputs of previous agents as context.

**Request:**
```json
{
  "message": "Write a blog post about LangGraph",
  "agent_ids": ["drafter-uuid", "reviewer-uuid", "editor-uuid"],
  "rounds": 1,
  "synthesis_prompt": "Combine all agent outputs into a final polished post."
}
```

**Validation:** Requires at least 2 agents.

**Response (200):**
```json
{
  "response": "Final polished blog post about LangGraph...",
  "agent_outputs": {
    "Drafter": "Initial draft of the blog post...",
    "Reviewer": "Review notes: improve intro...",
    "Editor": "Edited version with improvements..."
  },
  "pattern": "peer",
  "iterations": null
}
```

### Peer Flow

1. Agent 1 processes the user message directly
2. Agent 2 receives user message + Agent 1's output as context
3. Agent N receives user message + all previous outputs
4. If `synthesis_prompt` is provided, a final synthesis node combines all outputs
5. If no synthesis prompt, the last agent's output becomes the response

## GET /multi-agent/providers

List available LLM providers and models. No authentication required.

**Response (200):**
```json
{
  "openai": ["gpt-4o", "gpt-4o-mini"],
  "anthropic": ["claude-sonnet-4-20250514", "claude-haiku-4-5-20251001"]
}
```

## Schemas

| Schema              | Fields                                                    |
|---------------------|-----------------------------------------------------------|
| `SupervisorRequest` | `message`, `agent_ids[]`, `max_iterations` (default 10)   |
| `PeerRequest`       | `message`, `agent_ids[]`, `rounds` (default 1), `synthesis_prompt?` |
| `MultiAgentResponse`| `response`, `agent_outputs: dict`, `pattern`, `iterations?` |
