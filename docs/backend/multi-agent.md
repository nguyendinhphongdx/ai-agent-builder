---
id: multi-agent
title: Multi-Agent Orchestration
domain: backend
tags: [multi-agent, supervisor, peer, langgraph, collaboration]
related: [agent-executor, table-agents]
summary: Two multi-agent patterns built on LangGraph -- supervisor (hub-and-spoke delegation) and peer (sequential collaboration chain).
---

# Multi-Agent Orchestration

Source: `apps/backend/app/multi_agent/`

## Overview

The multi-agent module provides two orchestration patterns that coordinate multiple `Agent` instances through LangGraph state graphs. Both patterns reuse `build_agent_tools` and `build_llm_from_agent` from the agent executor.

## Supervisor Pattern (`supervisor.py`)

A central supervisor agent decides which worker agent should handle each sub-task, evaluates results, and either delegates again or produces a final answer.

### Architecture

```
User message -> Supervisor -> Worker A -> Supervisor -> Worker B -> Supervisor -> FINISH
```

### SupervisorState

| Key | Type | Purpose |
|---|---|---|
| `messages` | `list[BaseMessage]` | Full conversation history shared across all nodes. |
| `next_worker` | `str` | Name of the next worker to invoke, or `"FINISH"`. |
| `worker_results` | `dict[str, str]` | Accumulated results keyed by worker name. |
| `iterations` | `int` | Loop counter for infinite-loop protection. |

### Routing

The supervisor LLM receives a system prompt listing all workers with descriptions. It must respond with `ROUTE: <worker_name>` or `ROUTE: FINISH`. The `_parse_route` function extracts the directive (case-insensitive match).

After each worker completes, control returns to the supervisor node via a direct edge. The supervisor then re-evaluates with the accumulated `worker_results`.

### Loop Protection

Execution terminates when `iterations >= max_iterations` (default 10) or the supervisor returns `FINISH`.

### `run_supervisor(supervisor_agent, worker_agents, user_message, db, max_iterations)`

Returns `{"response": str, "worker_results": dict, "iterations": int}`.

## Peer Collaboration Pattern (`peer.py`)

Agents execute sequentially, each receiving the original user message plus outputs from all preceding agents.

### Architecture

```
User message -> Agent A -> Agent B -> Agent C -> [Synthesis] -> END
```

### PeerState

| Key | Type | Purpose |
|---|---|---|
| `messages` | `list[BaseMessage]` | Shared message history. |
| `agent_outputs` | `dict[str, str]` | Each agent's output keyed by name. |
| `current_round` | `int` | Round counter for multi-round debate. |

### Sequential Execution

- The first agent receives the user message directly.
- Subsequent agents receive the user message plus a formatted summary of all prior agent outputs as context.
- Each agent can use its own tools if configured.

### Synthesis Node

When `synthesis_prompt` is provided, a final synthesis node runs after the last agent. It receives all agent outputs and produces a consolidated answer. The LLM of the first agent is reused for synthesis.

### `run_peer_collaboration(agents, user_message, db, rounds, synthesis_prompt)`

Returns `{"response": str, "agent_outputs": dict}`. The `_synthesis` key is excluded from `agent_outputs` in the response.

## API Schemas (`schemas.py`)

| Schema | Fields | Notes |
|---|---|---|
| `SupervisorRequest` | `message`, `agent_ids`, `max_iterations` | `agent_ids[0]` is the supervisor; the rest are workers. |
| `PeerRequest` | `message`, `agent_ids`, `synthesis_prompt`, `rounds` | Agent order determines execution order. |
| `MultiAgentResponse` | `response`, `agent_outputs`, `pattern`, `iterations` | `pattern` is `"supervisor"` or `"peer"`. |

## Use Cases

- **Supervisor**: Task decomposition, delegation to specialist agents, quality control.
- **Peer debate**: Multiple viewpoints on the same question, then synthesis.
- **Review chain**: Writer agent -> Reviewer agent -> Editor agent.
- **Pipeline**: Each agent handles a different processing stage.
