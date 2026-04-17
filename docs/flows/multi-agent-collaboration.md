---
id: flows-multi-agent-collaboration
title: Multi-Agent Collaboration Flow
domain: flows
tags: [multi-agent, supervisor, peer, collaboration, langgraph, orchestration]
related: [api-multi-agent-endpoints, frontend-feature-agents-editor]
summary: End-to-end flow for both supervisor (delegate to workers) and peer (sequential chain) multi-agent patterns using LangGraph StateGraphs.
---

# Multi-Agent Collaboration Flow

## Overview

Two collaboration patterns are supported: **Supervisor** (one agent orchestrates workers) and **Peer** (agents process sequentially with shared context). Both are implemented as LangGraph StateGraphs.

## Supervisor Pattern

### Flow

```
User Message -> Supervisor -> [decides worker] -> Worker A executes
            -> Supervisor <- [receives result]
            -> [decides next] -> Worker B executes
            -> Supervisor <- [receives result]
            -> [FINISH] -> Final Response
```

### Step-by-Step

#### 1. API Call

```
POST /api/multi-agent/supervisor
{ "message": "...", "agent_ids": [supervisor_id, worker1_id, worker2_id], "max_iterations": 10 }
```

#### 2. Build Graph

`build_supervisor_graph()`:
- Builds LLM and tools for each agent
- Creates supervisor node with routing system prompt listing all workers and their descriptions
- Creates worker nodes, each with their own system prompt, LLM, and tools

#### 3. Supervisor Decides

Supervisor LLM receives:
- System prompt with worker names and descriptions
- User message
- Previous worker results (if any)

Responds with `ROUTE: <worker_name>` or `ROUTE: FINISH`.

`_parse_route()` extracts the target (case-insensitive matching).

#### 4. Worker Executes

Selected worker:
1. Receives the latest message content as task
2. Executes with its own system prompt and tools (via `create_react_agent` if tools exist)
3. Returns result appended to `worker_results` dict and messages

#### 5. Loop

Worker result flows back to supervisor. Supervisor evaluates and either:
- Routes to another worker
- Returns FINISH

Guard: loop terminates after `max_iterations` regardless.

#### 6. Return

Final supervisor message becomes the `response`. All worker outputs returned in `agent_outputs`.

### Supervisor State

| Field           | Type              | Description                    |
|-----------------|-------------------|--------------------------------|
| `messages`      | `list[BaseMessage]`| Full conversation history     |
| `next_worker`   | `str`             | Next worker name or "FINISH"  |
| `worker_results`| `dict[str, str]`  | Results per worker            |
| `iterations`    | `int`             | Loop counter                  |

## Peer Pattern

### Flow

```
User Message -> Agent A -> Agent B -> Agent C -> [Synthesis?] -> Final Response
```

### Step-by-Step

#### 1. API Call

```
POST /api/multi-agent/peer
{ "message": "...", "agent_ids": [a_id, b_id, c_id], "rounds": 1, "synthesis_prompt": "Combine outputs..." }
```

#### 2. Build Graph

`build_peer_graph()`:
- Creates a node for each agent in order
- Chains them sequentially: A -> B -> C
- Optionally adds synthesis node at the end

#### 3. Sequential Execution

- **Agent A** (first): receives user message directly, processes with own LLM/tools
- **Agent B** (subsequent): receives user message + all previous agent outputs as context
- **Agent C**: receives user message + Agent A + Agent B outputs

Each agent adds its output to `agent_outputs` dict.

#### 4. Synthesis (Optional)

If `synthesis_prompt` is provided:
- A final node receives all agent outputs
- Uses the first agent's LLM
- Generates a combined response following the synthesis prompt
- Result stored as `_synthesis` in agent outputs

#### 5. Return

If synthesis exists, `_synthesis` becomes the response. Otherwise, the last agent's output is the response.

### Peer State

| Field           | Type              | Description                    |
|-----------------|-------------------|--------------------------------|
| `messages`      | `list[BaseMessage]`| Shared conversation history   |
| `agent_outputs` | `dict[str, str]`  | Each agent's output           |
| `current_round` | `int`             | Round counter (for debate)    |

## Use Cases

**Supervisor pattern:**
- Research coordinator delegating to specialized researchers
- Support routing to department-specific agents
- Project manager assigning tasks to specialist agents

**Peer pattern:**
- Debate: agents argue different perspectives
- Review chain: draft -> review -> edit
- Pipeline: each agent handles a different processing step
