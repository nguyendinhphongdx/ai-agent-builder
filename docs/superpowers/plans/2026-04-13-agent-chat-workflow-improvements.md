# Agent Chat & Workflow Improvements - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve agent chat quality (retriever, KB mode, system prompt), add agent node to workflow, and harden security (code sandbox service, safe expression eval).

**Architecture:** Three independent phases that can execute in parallel. Phase 1 fixes the retriever and agent executor for better chat. Phase 2 adds agent node + LLM api_key to workflow. Phase 3 adds a code sandbox service and replaces eval() with simpleeval.

**Tech Stack:** Python/FastAPI, LangGraph, pgvector, simpleeval, Docker, Next.js/React Flow

---

## File Structure

### Phase 1: Agent Chat Quality
- Modify: `apps/backend/app/knowledge/retriever.py` — use KB config, add score threshold, return metadata
- Create: `apps/backend/app/knowledge/embeddings.py` — shared embedding factory extracted from ingestion
- Modify: `apps/backend/app/knowledge/ingestion.py` — use shared embedding factory
- Modify: `apps/backend/app/models/agent.py` — add `kb_retrieval_mode` field
- Modify: `apps/backend/app/agents/schemas.py` — add `kb_retrieval_mode` to schemas
- Modify: `apps/backend/app/agents/executor.py` — fix system prompt, implement auto/tool KB mode

### Phase 2: Workflow Enhancement
- Modify: `apps/backend/app/workflows/nodes/executor.py` — add agent node executor, fix LLM node api_key
- Modify: `apps/backend/app/workflows/compiler.py` — register agent node type
- Modify: `apps/frontend/src/features/workflows/types/index.ts` — add "agent" to WorkflowNodeType
- Modify: `apps/frontend/src/features/workflows/constants.ts` — add agent node definition

### Phase 3: Security
- Create: `services/code-sandbox/Dockerfile`
- Create: `services/code-sandbox/docker-compose.yml`
- Create: `services/code-sandbox/requirements.txt`
- Create: `services/code-sandbox/api/main.py` — FastAPI sandbox service
- Create: `services/code-sandbox/api/executor.py` — subprocess runner with resource limits
- Modify: `apps/backend/app/tools/registry.py` — CodeExecToolBuilder calls sandbox via HTTP
- Modify: `apps/backend/app/workflows/nodes/executor.py` — condition node uses simpleeval
- Modify: `apps/backend/pyproject.toml` — add simpleeval dependency
- Modify: `docker-compose.yml` (root) — add code-sandbox service include

---

## Phase 1: Agent Chat Quality

### Task 1: Extract shared embedding factory

**Files:**
- Create: `apps/backend/app/knowledge/embeddings.py`
- Modify: `apps/backend/app/knowledge/ingestion.py:83-94`

- [ ] **Step 1: Create embedding factory**

Create `apps/backend/app/knowledge/embeddings.py`:

```python
"""Shared embedding model factory for knowledge base operations."""
from __future__ import annotations

from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings


def build_embeddings(
    provider: str = "openai",
    model: str = "text-embedding-3-small",
    dimensions: int = 1536,
) -> Embeddings:
    """Build embedding model from KB config.

    Currently supports OpenAI. Add new providers as elif branches.
    """
    if provider == "openai":
        return OpenAIEmbeddings(model=model, dimensions=dimensions)

    # Default fallback to OpenAI
    return OpenAIEmbeddings(model=model, dimensions=dimensions)
```

- [ ] **Step 2: Update ingestion.py to use shared factory**

In `apps/backend/app/knowledge/ingestion.py`, replace the `_get_embeddings` function (lines 83-94):

```python
# Remove this:
def _get_embeddings(kb: KnowledgeBase):
    """Get embedding model based on KB config."""
    if kb.embedding_provider == "openai":
        return OpenAIEmbeddings(
            model=kb.embedding_model,
            dimensions=kb.embedding_dimensions,
        )
    # Default to OpenAI
    return OpenAIEmbeddings(
        model=kb.embedding_model,
        dimensions=kb.embedding_dimensions,
    )

# Replace with:
from app.knowledge.embeddings import build_embeddings

def _get_embeddings(kb: KnowledgeBase):
    """Get embedding model based on KB config."""
    return build_embeddings(
        provider=kb.embedding_provider,
        model=kb.embedding_model,
        dimensions=kb.embedding_dimensions,
    )
```

Also remove the now-unused import `from langchain_openai import OpenAIEmbeddings` at line 4.

- [ ] **Step 3: Verify ingestion still works**

Run: `cd apps/backend && python -c "from app.knowledge.ingestion import ingest_document; print('OK')"`
Expected: OK

---

### Task 2: Fix KnowledgeRetriever

**Files:**
- Modify: `apps/backend/app/knowledge/retriever.py`

- [ ] **Step 1: Rewrite retriever to use KB config**

Replace the entire `apps/backend/app/knowledge/retriever.py`:

```python
"""Vector similarity search across knowledge bases using pgvector."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.knowledge.embeddings import build_embeddings
from app.models.document_chunk import DocumentChunk
from app.models.knowledge_base import KnowledgeBase


@dataclass
class RetrievedChunk:
    content: str
    metadata: dict
    score: float | None = None
    source_document: str | None = None
    chunk_index: int | None = None


class KnowledgeRetriever:
    """Performs similarity search across one or more knowledge bases."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def retrieve(
        self,
        query: str,
        knowledge_base_ids: list[uuid.UUID],
        top_k: int | None = None,
        score_threshold: float | None = None,
    ) -> list[RetrievedChunk]:
        if not knowledge_base_ids:
            return []

        # Load KB configs to get embedding settings and retrieval params
        result = await self.db.execute(
            select(KnowledgeBase).where(KnowledgeBase.id.in_(knowledge_base_ids))
        )
        kbs = result.scalars().all()
        if not kbs:
            return []

        # Use first KB's config for embedding (all KBs in same query should share embedding config)
        kb = kbs[0]
        effective_top_k = top_k or kb.retrieval_top_k or 5
        effective_threshold = score_threshold if score_threshold is not None else kb.retrieval_score_threshold

        # Build embeddings from KB config
        embeddings = build_embeddings(
            provider=kb.embedding_provider,
            model=kb.embedding_model,
            dimensions=kb.embedding_dimensions,
        )

        # Embed the query
        query_embedding = await embeddings.aembed_query(query)

        # pgvector cosine distance search
        db_result = await self.db.execute(
            select(
                DocumentChunk.content,
                DocumentChunk.data,
                DocumentChunk.embedding.cosine_distance(query_embedding).label("distance"),
            )
            .where(DocumentChunk.knowledge_base_id.in_(knowledge_base_ids))
            .where(DocumentChunk.embedding.isnot(None))
            .order_by("distance")
            .limit(effective_top_k)
        )

        chunks = []
        for row in db_result.all():
            similarity = 1.0 - (row.distance or 0)

            # Filter by score threshold
            if effective_threshold is not None and similarity < effective_threshold:
                continue

            metadata = row.data or {}
            chunks.append(
                RetrievedChunk(
                    content=row.content,
                    metadata=metadata,
                    score=similarity,
                    source_document=metadata.get("source"),
                    chunk_index=metadata.get("chunk_index"),
                )
            )

        return chunks
```

- [ ] **Step 2: Verify retriever imports**

Run: `cd apps/backend && python -c "from app.knowledge.retriever import KnowledgeRetriever, RetrievedChunk; print('OK')"`
Expected: OK

---

### Task 3: Add kb_retrieval_mode to Agent

**Files:**
- Modify: `apps/backend/app/models/agent.py:59` (after `status` field)
- Modify: `apps/backend/app/agents/schemas.py`

- [ ] **Step 1: Add field to Agent model**

In `apps/backend/app/models/agent.py`, add after line 59 (`status` field):

```python
    kb_retrieval_mode: Mapped[str] = mapped_column(String(20), default="tool")  # "auto" hoặc "tool"
```

- [ ] **Step 2: Add to AgentCreate schema**

In `apps/backend/app/agents/schemas.py`, add to `AgentCreate` (after `max_turns` at line 17):

```python
    kb_retrieval_mode: str = "tool"
```

- [ ] **Step 3: Add to AgentUpdate schema**

In `apps/backend/app/agents/schemas.py`, add to `AgentUpdate` (after `avatar_url` at line 31):

```python
    kb_retrieval_mode: str | None = None
```

- [ ] **Step 4: Add to AgentResponse schema**

In `apps/backend/app/agents/schemas.py`, add to `AgentResponse` (after `max_turns` at line 60):

```python
    kb_retrieval_mode: str
```

- [ ] **Step 5: Create Alembic migration**

Run: `cd apps/backend && alembic revision --autogenerate -m "add kb_retrieval_mode to agents"`
Then run: `cd apps/backend && alembic upgrade head`

---

### Task 4: Fix executor — system prompt + KB retrieval modes

**Files:**
- Modify: `apps/backend/app/agents/executor.py`

- [ ] **Step 1: Rewrite executor.py**

Replace the entire `apps/backend/app/agents/executor.py`:

```python
"""LangGraph-based agent executor with tool support and streaming."""
from __future__ import annotations

import uuid
from typing import AsyncGenerator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langgraph.prebuilt import create_react_agent
from sqlalchemy.ext.asyncio import AsyncSession

from app.knowledge.retriever import KnowledgeRetriever
from app.llm.provider import build_llm_from_agent
from app.models.agent import Agent
from app.tools.registry import tool_registry


def _build_history(messages: list) -> list:
    """Convert DB messages to LangChain message objects.

    System prompt is NOT included here — it is passed via state_modifier.
    """
    lc_messages = []

    for msg in messages:
        if msg.role == "user":
            lc_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            lc_messages.append(AIMessage(content=msg.content))
        elif msg.role == "tool":
            lc_messages.append(
                ToolMessage(content=msg.content, tool_call_id=msg.tool_call_id or "")
            )

    return lc_messages


async def _auto_retrieve_context(
    agent: Agent, messages: list, db: AsyncSession
) -> str | None:
    """Auto-retrieve relevant KB chunks for the latest user message.

    Returns formatted context string or None if no results.
    """
    if not agent.knowledge_bases:
        return None

    # Find latest user message
    latest_user_msg = None
    for msg in reversed(messages):
        if msg.role == "user":
            latest_user_msg = msg.content
            break

    if not latest_user_msg:
        return None

    retriever = KnowledgeRetriever(db)
    kb_ids = [kb.id for kb in agent.knowledge_bases]
    chunks = await retriever.retrieve(latest_user_msg, kb_ids)

    if not chunks:
        return None

    formatted_chunks = []
    for c in chunks:
        source = f" (source: {c.source_document})" if c.source_document else ""
        formatted_chunks.append(f"{c.content}{source}")

    return "\n\n---\n\n".join(formatted_chunks)


def _build_system_prompt(base_prompt: str | None, kb_context: str | None) -> str | None:
    """Combine system prompt with auto-retrieved KB context."""
    parts = []
    if base_prompt:
        parts.append(base_prompt)
    if kb_context:
        parts.append(f"\n\n## Relevant Knowledge:\n{kb_context}")
    return "\n".join(parts) if parts else None


async def build_agent_tools(
    agent: Agent, db: AsyncSession
) -> list[StructuredTool]:
    """Build all tools for an agent: custom tools + RAG retrieval tool (if mode=tool)."""
    tools: list[StructuredTool] = []

    # Custom tools attached to the agent
    if agent.tools:
        tools.extend(tool_registry.build_many(agent.tools))

    # Knowledge base retrieval tool — only in "tool" mode
    if agent.knowledge_bases and agent.kb_retrieval_mode == "tool":
        retriever = KnowledgeRetriever(db)
        kb_ids = [kb.id for kb in agent.knowledge_bases]
        kb_names = ", ".join(kb.name for kb in agent.knowledge_bases)

        async def search_knowledge(query: str) -> str:
            """Search the agent's knowledge base for relevant information."""
            chunks = await retriever.retrieve(query, kb_ids)
            if not chunks:
                return "No relevant information found."
            results = []
            for c in chunks:
                source = f" (source: {c.source_document})" if c.source_document else ""
                results.append(f"{c.content}{source}")
            return "\n\n---\n\n".join(results)

        from langchain_core.tools import tool as tool_decorator

        @tool_decorator(description=f"Search knowledge bases ({kb_names}) for relevant information about the query.")
        async def search_knowledge_base(query: str) -> str:
            """Search knowledge bases for relevant information."""
            return await search_knowledge(query)

        tools.append(search_knowledge_base)

    return tools


class AgentStreamEvent:
    """Events emitted during agent execution."""

    def __init__(self, event_type: str, **kwargs):
        self.type = event_type
        self.data = kwargs

    def to_dict(self) -> dict:
        return {"type": self.type, **self.data}


async def execute_agent_stream(
    agent: Agent,
    messages: list,
    db: AsyncSession,
    api_key: str | None = None,
) -> AsyncGenerator[AgentStreamEvent, None]:
    """Execute agent with LangGraph and yield streaming events."""
    llm = build_llm_from_agent(agent, api_key=api_key)
    tools = await build_agent_tools(agent, db)
    lc_messages = _build_history(messages)

    # Build system prompt (with auto KB context if mode=auto)
    kb_context = None
    if agent.kb_retrieval_mode == "auto":
        kb_context = await _auto_retrieve_context(agent, messages, db)

    system_prompt = _build_system_prompt(agent.system_prompt, kb_context)

    if tools:
        # Use LangGraph ReAct agent with tools
        # Pass system prompt via state_modifier for correct placement
        graph = create_react_agent(llm, tools, state_modifier=system_prompt)

        async for event in graph.astream_events(
            {"messages": lc_messages},
            version="v2",
        ):
            kind = event["event"]

            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if hasattr(chunk, "content") and chunk.content:
                    yield AgentStreamEvent("token", content=chunk.content)

            elif kind == "on_tool_start":
                yield AgentStreamEvent(
                    "tool_start",
                    name=event["name"],
                    input=str(event["data"].get("input", ""))[:500],
                )

            elif kind == "on_tool_end":
                yield AgentStreamEvent(
                    "tool_end",
                    name=event["name"],
                    result=str(event["data"].get("output", ""))[:500],
                )
    else:
        # Simple streaming without tools
        pre_messages = []
        if system_prompt:
            pre_messages.append(SystemMessage(content=system_prompt))
        pre_messages.extend(lc_messages)

        async for chunk in llm.astream(pre_messages):
            if hasattr(chunk, "content") and chunk.content:
                yield AgentStreamEvent("token", content=chunk.content)

    yield AgentStreamEvent("done")
```

- [ ] **Step 2: Verify executor imports**

Run: `cd apps/backend && python -c "from app.agents.executor import execute_agent_stream, build_agent_tools; print('OK')"`
Expected: OK

---

## Phase 2: Workflow Enhancement

### Task 5: Add agent node executor

**Files:**
- Modify: `apps/backend/app/workflows/nodes/executor.py`

- [ ] **Step 1: Add agent node executor function**

In `apps/backend/app/workflows/nodes/executor.py`, add the following imports at the top (after existing imports):

```python
from app.agents.executor import build_agent_tools, _build_system_prompt, _auto_retrieve_context
from app.agents.service import get_agent
from app.api_keys.service import get_plaintext_key_for_provider
from app.llm.provider import build_llm_from_agent
from langgraph.prebuilt import create_react_agent
```

- [ ] **Step 2: Add the execute_agent_node function**

Add before the `NODE_EXECUTORS` dict at the bottom of `apps/backend/app/workflows/nodes/executor.py`:

```python
# ─── Agent Node ───────────────────────────────────────────────────

async def execute_agent_node(state: dict, config: dict, node_id: str, label: str | None, db: AsyncSession = None, **kwargs) -> dict:
    """Node Agent: gọi agent đã build sẵn với dữ liệu từ state.

    Config cần có:
    - agent_id: UUID của agent đã build
    - output_mode: "text" (mặc định) hoặc "structured"
    """
    started = _now_iso()
    input_data = state.get("data", {})

    try:
        agent_id = config.get("agent_id")
        if not agent_id:
            raise ValueError("agent_id is required in agent node config")

        if db is None:
            raise ValueError("Database session required for agent node")

        # Load agent with tools + knowledge_bases
        from app.models.agent import Agent as AgentModel
        result = await db.execute(
            select(AgentModel).where(AgentModel.id == agent_id)
        )
        agent = result.scalar_one_or_none()
        if not agent:
            raise ValueError(f"Agent not found: {agent_id}")

        # Resolve API key from agent's owner
        api_key = await get_plaintext_key_for_provider(
            db, agent.user_id, agent.llm_provider
        )

        # Build LLM and tools
        llm = build_llm_from_agent(agent, api_key=api_key)
        tools = await build_agent_tools(agent, db)

        # Build system prompt with auto KB context if applicable
        kb_context = None
        if agent.kb_retrieval_mode == "auto":
            # Create a mock message object for _auto_retrieve_context
            class _Msg:
                def __init__(self, role, content):
                    self.role = role
                    self.content = content

            mock_messages = [_Msg("user", str(input_data) if not isinstance(input_data, str) else input_data)]
            kb_context = await _auto_retrieve_context(agent, mock_messages, db)

        system_prompt = _build_system_prompt(agent.system_prompt, kb_context)

        # Prepare user message
        user_content = str(input_data) if not isinstance(input_data, str) else input_data
        messages = [HumanMessage(content=user_content)]

        tokens_used = 0
        output_mode = config.get("output_mode", "text")

        if tools:
            graph = create_react_agent(llm, tools, state_modifier=system_prompt)
            result_state = await graph.ainvoke({"messages": messages})

            # Extract response and tool results
            final_messages = result_state.get("messages", [])
            response_text = ""
            tool_results = []
            for msg in final_messages:
                if hasattr(msg, "content") and isinstance(msg, AIMessage) and not msg.tool_calls:
                    response_text = msg.content
                elif hasattr(msg, "content") and isinstance(msg, ToolMessage):
                    tool_results.append({
                        "tool_call_id": msg.tool_call_id,
                        "content": msg.content[:500],
                    })
        else:
            pre_messages = []
            if system_prompt:
                pre_messages.append(SystemMessage(content=system_prompt))
            pre_messages.extend(messages)

            response = await llm.ainvoke(pre_messages)
            response_text = response.content
            tool_results = []

            if hasattr(response, "usage_metadata") and response.usage_metadata:
                tokens_used = response.usage_metadata.get("total_tokens", 0)

        # Set output based on mode
        if output_mode == "structured":
            state["data"] = {
                "response": response_text,
                "tool_results": tool_results,
                "sources": [],
            }
        else:
            state["data"] = response_text

        state["total_tokens"] = state.get("total_tokens", 0) + tokens_used

        state["node_logs"].append(_make_log(
            node_id=node_id, node_type="agent", label=label,
            status="completed",
            input_data={"agent": agent.name, "input": str(input_data)[:500]},
            output_data={"response": response_text[:500]},
            tokens_used=tokens_used,
            started_at=started, completed_at=_now_iso(),
        ))

    except Exception as e:
        state["node_logs"].append(_make_log(
            node_id=node_id, node_type="agent", label=label,
            status="failed", input_data=input_data,
            error=str(e), started_at=started, completed_at=_now_iso(),
        ))
        raise

    return state
```

- [ ] **Step 3: Register agent node in NODE_EXECUTORS**

In `apps/backend/app/workflows/nodes/executor.py`, update the `NODE_EXECUTORS` dict:

```python
NODE_EXECUTORS = {
    "input": execute_input_node,
    "output": execute_output_node,
    "llm": execute_llm_node,
    "tool": execute_tool_node,
    "condition": execute_condition_node,
    "human_input": execute_human_input_node,
    "agent": execute_agent_node,
}
```

- [ ] **Step 4: Verify import**

Run: `cd apps/backend && python -c "from app.workflows.nodes.executor import NODE_EXECUTORS; print(list(NODE_EXECUTORS.keys()))"`
Expected: `['input', 'output', 'llm', 'tool', 'condition', 'human_input', 'agent']`

---

### Task 6: Fix LLM node — require api_key in config

**Files:**
- Modify: `apps/backend/app/workflows/nodes/executor.py` (the `execute_llm_node` function)

- [ ] **Step 1: Update execute_llm_node to use api_key from config**

In `apps/backend/app/workflows/nodes/executor.py`, replace the `execute_llm_node` function (the `build_llm` call, around line 113):

Find this block:
```python
        llm = build_llm(
            provider=config.get("llm_provider", "openai"),
            model=config.get("llm_model", "gpt-4o"),
            temperature=config.get("temperature", 0.7),
            max_tokens=config.get("max_tokens", 4096),
            base_url=config.get("base_url"),
        )
```

Replace with:
```python
        api_key = config.get("api_key")
        if not api_key:
            raise ValueError("api_key is required in LLM node config")

        llm = build_llm(
            provider=config.get("llm_provider", "openai"),
            model=config.get("llm_model", "gpt-4o"),
            temperature=config.get("temperature", 0.7),
            max_tokens=config.get("max_tokens", 4096),
            base_url=config.get("base_url"),
            api_key=api_key,
        )
```

---

### Task 7: Frontend — add agent node to workflow editor

**Files:**
- Modify: `apps/frontend/src/features/workflows/types/index.ts`
- Modify: `apps/frontend/src/features/workflows/constants.ts`
- Modify: `apps/frontend/src/features/workflows/components/custom-nodes/BaseNode.tsx`
- Modify: `apps/frontend/src/features/workflows/components/NodePalette.tsx`

- [ ] **Step 1: Add "agent" to WorkflowNodeType**

In `apps/frontend/src/features/workflows/types/index.ts`, update the `WorkflowNodeType` union (line 36-45):

```typescript
export type WorkflowNodeType =
  | "start"
  | "end"
  | "llm"
  | "tool"
  | "condition"
  | "human_input"
  | "code"
  | "knowledge_retrieval"
  | "merge"
  | "agent";
```

- [ ] **Step 2: Add agent node definition to constants**

In `apps/frontend/src/features/workflows/constants.ts`, add the agent node definition to `NODE_TYPES` array (before the closing `];` at line 199):

```typescript
  {
    type: "agent",
    label: "Agent",
    description: "Run a pre-built agent",
    icon: "bot",
    color: "#6366f1",
    handles: { inputs: 1, outputs: 1 },
    configFields: [
      {
        key: "agent_id",
        label: "Agent",
        type: "select",
        options: [], // Populated dynamically
      },
      {
        key: "output_mode",
        label: "Output Mode",
        type: "select",
        options: [
          { label: "Text only", value: "text" },
          { label: "Structured (response + tool results)", value: "structured" },
        ],
        defaultValue: "text",
      },
    ],
  },
```

- [ ] **Step 3: Add Bot icon to icon maps**

In `apps/frontend/src/features/workflows/components/NodePalette.tsx`, add the `Bot` import (line 3):

```typescript
import {
  Play,
  Square,
  Brain,
  Wrench,
  GitBranch,
  User,
  BookOpen,
  Code,
  Layers,
  Bot,
} from "lucide-react";
```

Add to `ICON_MAP` (after `layers: Layers` at line 27):

```typescript
  bot: Bot,
```

Do the same in `apps/frontend/src/features/workflows/components/custom-nodes/BaseNode.tsx`:

Add `Bot` to the import (line 6):
```typescript
import {
  Play, Square, Brain, Wrench, GitBranch, User, BookOpen, Code, Layers, Bot,
} from "lucide-react";
```

Add to `ICON_MAP` (after `layers: Layers` at line 16):
```typescript
  bot: Bot,
```

- [ ] **Step 4: Add api_key and provider fields to LLM node config**

In `apps/frontend/src/features/workflows/constants.ts`, update the `llm` node's `configFields` array. Add these two fields at the beginning (before `llm_model`):

```typescript
      {
        key: "llm_provider",
        label: "Provider",
        type: "select",
        options: [
          { label: "OpenAI", value: "openai" },
          { label: "Anthropic", value: "anthropic" },
          { label: "Ollama", value: "ollama" },
        ],
        defaultValue: "openai",
      },
      {
        key: "api_key",
        label: "API Key",
        type: "text",
        placeholder: "sk-...",
      },
```

---

## Phase 3: Security

### Task 8: Create code sandbox service

**Files:**
- Create: `services/code-sandbox/Dockerfile`
- Create: `services/code-sandbox/docker-compose.yml`
- Create: `services/code-sandbox/requirements.txt`
- Create: `services/code-sandbox/api/__init__.py`
- Create: `services/code-sandbox/api/main.py`
- Create: `services/code-sandbox/api/executor.py`

- [ ] **Step 1: Create Dockerfile**

Create `services/code-sandbox/Dockerfile`:

```dockerfile
FROM python:3.12-slim

# Install Node.js and bash (bash already included in slim)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Create non-root user for running sandboxed code
RUN useradd -m -s /bin/bash sandbox

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ ./api/

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Create requirements.txt**

Create `services/code-sandbox/requirements.txt`:

```
fastapi>=0.115
uvicorn[standard]>=0.30
```

- [ ] **Step 3: Create executor module**

Create `services/code-sandbox/api/__init__.py` (empty file).

Create `services/code-sandbox/api/executor.py`:

```python
"""Sandboxed code execution with resource limits."""
from __future__ import annotations

import asyncio
import os
import tempfile
import time

LANGUAGE_CONFIG = {
    "python": {"command": ["python3"], "ext": ".py"},
    "javascript": {"command": ["node"], "ext": ".js"},
    "bash": {"command": ["bash"], "ext": ".sh"},
}

SUPPORTED_LANGUAGES = set(LANGUAGE_CONFIG.keys())


async def execute_code(
    code: str,
    language: str = "python",
    timeout: int = 30,
) -> dict:
    """Execute code in a subprocess with resource limits.

    Returns dict with output, exit_code, error, execution_time_ms.
    """
    if language not in LANGUAGE_CONFIG:
        return {
            "output": "",
            "exit_code": 1,
            "error": f"Unsupported language: {language}. Supported: {', '.join(SUPPORTED_LANGUAGES)}",
            "execution_time_ms": 0,
        }

    lang_config = LANGUAGE_CONFIG[language]

    # Write code to temp file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=lang_config["ext"], delete=False, dir="/tmp"
    ) as f:
        f.write(code)
        tmp_path = f.name

    try:
        start = time.monotonic()

        # Run as sandbox user with resource limits
        cmd = [
            "su", "-s", "/bin/bash", "sandbox", "-c",
            f"ulimit -v 131072 -t {timeout} && {' '.join(lang_config['command'])} {tmp_path}"
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            elapsed = int((time.monotonic() - start) * 1000)
            return {
                "output": "",
                "exit_code": -1,
                "error": f"Execution timed out after {timeout}s",
                "execution_time_ms": elapsed,
            }

        elapsed = int((time.monotonic() - start) * 1000)
        output = stdout.decode("utf-8", errors="replace")
        error = stderr.decode("utf-8", errors="replace")

        return {
            "output": output[:10000],
            "exit_code": proc.returncode,
            "error": error[:5000] if error else None,
            "execution_time_ms": elapsed,
        }

    finally:
        os.unlink(tmp_path)
```

- [ ] **Step 4: Create FastAPI main**

Create `services/code-sandbox/api/main.py`:

```python
"""Code Sandbox Service — lightweight HTTP API for sandboxed code execution."""
from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import FastAPI

from api.executor import execute_code, SUPPORTED_LANGUAGES

app = FastAPI(title="Code Sandbox", version="1.0.0")


class ExecuteRequest(BaseModel):
    code: str
    language: str = "python"
    timeout: int = Field(default=30, ge=1, le=120)


class ExecuteResponse(BaseModel):
    output: str
    exit_code: int
    error: str | None
    execution_time_ms: int


@app.post("/execute", response_model=ExecuteResponse)
async def execute(req: ExecuteRequest) -> ExecuteResponse:
    result = await execute_code(
        code=req.code,
        language=req.language,
        timeout=req.timeout,
    )
    return ExecuteResponse(**result)


@app.get("/health")
async def health():
    return {"status": "ok", "languages": list(SUPPORTED_LANGUAGES)}
```

- [ ] **Step 5: Create docker-compose.yml for sandbox**

Create `services/code-sandbox/docker-compose.yml`:

```yaml
services:
  code-sandbox:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8100:8000"
    networks:
      - agentforge
    mem_limit: 512m
    cpus: 1.0
    restart: unless-stopped

networks:
  agentforge:
    external: true
```

- [ ] **Step 6: Add sandbox to root docker-compose.yml**

In the root `docker-compose.yml`, add to the `include:` list:

```yaml
  - path: services/code-sandbox/docker-compose.yml
```

And add `code-sandbox` to the backend service `depends_on`:

```yaml
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      code-sandbox:
        condition: service_started
```

---

### Task 9: Update CodeExecToolBuilder to use sandbox service

**Files:**
- Modify: `apps/backend/app/tools/registry.py`

- [ ] **Step 1: Replace CodeExecToolBuilder implementation**

In `apps/backend/app/tools/registry.py`, replace the `CodeExecToolBuilder` class (lines 87-125):

```python
class CodeExecToolBuilder(ToolBuilder):
    """Builder cho tool code execution - gọi sandbox service qua HTTP."""

    SANDBOX_URL = "http://code-sandbox:8000/execute"

    def build(self, tool_def: Tool) -> StructuredTool:
        config = tool_def.config

        async def execute(**kwargs) -> str:
            import httpx

            code = config.get("code_template", "")
            for key, val in kwargs.items():
                code = code.replace(f"{{{key}}}", str(val))

            language = config.get("language", "python")

            async with httpx.AsyncClient(timeout=tool_def.timeout_seconds + 5) as client:
                try:
                    resp = await client.post(
                        CodeExecToolBuilder.SANDBOX_URL,
                        json={
                            "code": code,
                            "language": language,
                            "timeout": tool_def.timeout_seconds,
                        },
                    )
                    resp.raise_for_status()
                    result = resp.json()

                    if result.get("error"):
                        return f"Output:\n{result['output']}\n\nError:\n{result['error']}"
                    return result["output"][:4000]

                except httpx.ConnectError:
                    return "Error: Code sandbox service is not available."

        args_schema = json_schema_to_pydantic(tool_def.input_schema)

        return StructuredTool.from_function(
            coroutine=execute,
            name=tool_def.name.replace(" ", "_").lower(),
            description=tool_def.description,
            args_schema=args_schema,
        )
```

---

### Task 10: Replace eval() with simpleeval in condition node

**Files:**
- Modify: `apps/backend/pyproject.toml`
- Modify: `apps/backend/app/workflows/nodes/executor.py`

- [ ] **Step 1: Add simpleeval dependency**

In `apps/backend/pyproject.toml`, add to the `dependencies` list:

```
    "simpleeval>=1.0",
```

- [ ] **Step 2: Install dependency**

Run: `cd apps/backend && pip install simpleeval`

- [ ] **Step 3: Update execute_condition_node**

In `apps/backend/app/workflows/nodes/executor.py`, replace the `execute_condition_node` function. Find this block (around line 237):

```python
        eval_result = eval(expression, {"__builtins__": {}}, {"data": input_data})
```

Replace with:

```python
        from simpleeval import simple_eval, EvalWithCompoundTypes
        eval_result = simple_eval(expression, names={"data": input_data})
```

- [ ] **Step 4: Verify simpleeval works**

Run: `cd apps/backend && python -c "from simpleeval import simple_eval; print(simple_eval('data > 5', names={'data': 10}))"`
Expected: `True`

---

## Summary of all changes

| Phase | Task | Files Changed | Description |
|-------|------|---------------|-------------|
| 1 | Task 1 | embeddings.py (new), ingestion.py | Extract shared embedding factory |
| 1 | Task 2 | retriever.py | Use KB config, score threshold, metadata |
| 1 | Task 3 | agent model + schemas | Add kb_retrieval_mode field |
| 1 | Task 4 | executor.py | Fix system prompt + KB auto/tool modes |
| 2 | Task 5 | nodes/executor.py, compiler.py | Add agent node executor |
| 2 | Task 6 | nodes/executor.py | LLM node require api_key |
| 2 | Task 7 | Frontend types, constants, components | Agent node in workflow editor |
| 3 | Task 8 | services/code-sandbox/ (new) | Sandbox service |
| 3 | Task 9 | registry.py | CodeExec calls sandbox via HTTP |
| 3 | Task 10 | nodes/executor.py, pyproject.toml | simpleeval for condition node |
