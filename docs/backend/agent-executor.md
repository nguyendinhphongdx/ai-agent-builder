---
id: agent-executor
title: Agent Executor
domain: backend
tags: [langgraph, streaming, tools, rag, executor]
related: [table-agents, table-tools, table-knowledge, multi-agent]
summary: LangGraph-based agent executor that builds LLM instances, assembles tool sets, and streams execution events to callers.
---

# Agent Executor

Source: `apps/backend/app/modules/studio/agents/executor.py`

## Overview

The agent executor is the runtime core of lc-agent. It takes an `Agent` model, converts the conversation history into LangChain message objects, builds the tool set, and executes the agent through LangGraph's ReAct loop while yielding streaming events.

## Key Functions

### `_build_history(messages, system_prompt)`

Converts persisted database `Message` rows into LangChain message objects (`SystemMessage`, `HumanMessage`, `AIMessage`, `ToolMessage`). The system prompt, when present, is prepended as the first message.

### `build_agent_tools(agent, db) -> list[StructuredTool]`

Assembles the complete tool list for an agent from two sources:

| Source | Mechanism |
|---|---|
| **Custom tools** | Resolved via `tool_registry.build_many(agent.tools)` from the N-N `agent_tools` relation. |
| **Knowledge base retrieval** | A dynamic `search_knowledge_base` tool is created when `agent.knowledge_bases` is non-empty. It calls `KnowledgeRetriever.retrieve()` across all linked KB IDs and joins matching chunks with `---` separators. |

The RAG tool's docstring is dynamically generated to include knowledge base names, giving the LLM awareness of what knowledge is available.

### `execute_agent_stream(agent, messages, db) -> AsyncGenerator[AgentStreamEvent]`

Entry point for running an agent. The execution path depends on whether the agent has tools:

**With tools** -- A LangGraph `create_react_agent(llm, tools)` graph is created and executed via `graph.astream_events(version="v2")`. The executor listens for three LangGraph event kinds and maps them to `AgentStreamEvent` instances.

**Without tools** -- The LLM is called directly via `llm.astream()` and each content chunk is yielded as a `token` event.

Both paths emit a final `done` event.

## LLM Construction

The LLM instance is built by `build_llm_from_agent(agent)` (in `app.modules.integrations.llm.provider`), which reads `agent.llm_provider`, `agent.llm_model`, and `agent.llm_config` to construct the appropriate LangChain chat model.

## AgentStreamEvent

A lightweight event wrapper emitted during streaming. Each event has a `type` string and arbitrary `data` kwargs.

### Event Types

| Type | Data Fields | Description |
|---|---|---|
| `token` | `content: str` | A content chunk from the LLM response. |
| `tool_start` | `name: str`, `input: str` | A tool invocation has begun. Input is truncated to 500 chars. |
| `tool_end` | `name: str`, `result: str` | A tool invocation completed. Result is truncated to 500 chars. |
| `done` | _(none)_ | The agent has finished execution. |

### Serialization

`AgentStreamEvent.to_dict()` returns `{"type": ..., **data}`, suitable for SSE or WebSocket delivery.

## Execution Flow

```
Client request
  -> execute_agent_stream()
      -> build_llm_from_agent()      # construct LLM
      -> build_agent_tools()          # custom tools + RAG tool
      -> _build_history()             # DB messages -> LangChain messages
      -> create_react_agent() | llm.astream()
          -> yield token / tool_start / tool_end events
      -> yield done
```

## Error Handling

Exceptions raised during tool execution or LLM calls propagate out of the async generator. Callers are responsible for catching errors and mapping them to appropriate API responses.
