# Agent Chat & Workflow Improvements - Design Spec

## Overview

Improve agent chat quality, add agent node to workflow, and harden security. Three phases that can be executed in parallel.

---

## Phase 1: Agent Chat Quality

### 1.1 Fix Retriever (`app/knowledge/retriever.py`)

**Problem:** Hardcoded `OpenAIEmbeddings(model="text-embedding-3-small")`, hardcoded `top_k=5`, no score filtering, no metadata in results.

**Changes:**

- Constructor accepts `embedding_provider`, `embedding_model`, `embedding_dimensions` from KB config
- Use shared `_get_embeddings()` factory from `ingestion.py` (extract to `app/knowledge/embeddings.py`)
- `retrieve()` accepts `top_k` from caller (sourced from KB's `retrieval_top_k`)
- Add `score_threshold` param (default `0.3`) — filter chunks with similarity below threshold
- `RetrievedChunk` returns `source_document` (filename) and `chunk_index` from chunk metadata

**Interface:**

```python
class KnowledgeRetriever:
    def __init__(self, db, embedding_provider, embedding_model, embedding_dimensions):
        ...

    async def retrieve(self, query, kb_ids, top_k=5, score_threshold=0.3) -> list[RetrievedChunk]:
        ...

@dataclass
class RetrievedChunk:
    content: str
    metadata: dict
    score: float | None = None
    source_document: str | None = None
    chunk_index: int | None = None
```

### 1.2 KB Retrieval Mode on Agent

**Problem:** KB is only available as a tool — LLM must decide to call it. If LLM doesn't think to search, KB is ignored entirely.

**Changes:**

- Add field to Agent model: `kb_retrieval_mode: str = "tool"` (values: `"auto"` | `"tool"`)
- Mode `auto`: before calling LLM, query KB with latest user message → inject top-k chunks into SystemMessage as `\n\n## Relevant Knowledge:\n{chunks_with_sources}`
- Mode `tool`: keep current logic (create `search_knowledge_base` tool for LLM to call)
- Both modes use the fixed retriever

**Affected files:** `app/models/agent.py`, `app/agents/executor.py`, `app/schemas/agent.py`

### 1.3 Fix System Prompt in ReAct Agent

**Problem:** System prompt appended as first message in history. `create_react_agent()` has its own system prompt for tool instructions. User's system prompt gets buried in context.

**Change:**

```python
# Before
lc_messages = _build_history(messages, agent.system_prompt)
graph = create_react_agent(llm, tools)

# After
lc_messages = _build_history(messages, system_prompt=None)  # no system prompt in history
graph = create_react_agent(llm, tools, state_modifier=agent.system_prompt)
```

`create_react_agent` with `state_modifier` as string prepends SystemMessage correctly, merged with tool instructions.

**Affected files:** `app/agents/executor.py`

---

## Phase 2: Workflow Enhancement

### 2.1 Agent Node (new node type: `agent`)

**Purpose:** Use an already-built agent in workflow instead of configuring LLM from scratch.

**Config:**

```python
{
    "agent_id": "uuid",
    "output_mode": "text"  # "text" | "structured"
}
```

**Executor logic:**

1. Load agent from DB (with tools + knowledge_bases via `selectin`)
2. Resolve api_key: `agent.user_id` + `agent.llm_provider` → lookup `api_keys` table
3. Reuse `build_agent_tools()` and `build_llm_from_agent()` from existing executor
4. Build ReAct graph, invoke with `state["data"]` as user message
5. Collect full response (non-streaming since workflow runs batch)
6. Output:
   - `text` mode: `state["data"] = response_text`
   - `structured` mode: `state["data"] = {"response": text, "tool_results": [...], "sources": [...]}`

**API key resolution:** Agent knows its owner (`agent.user_id`) → lookup encrypted key from `api_keys` table → decrypt → pass to LLM. No need to modify WorkflowState or pass user_id through state.

**Affected files:** `app/workflows/nodes/executor.py`, `app/workflows/compiler.py`

### 2.2 LLM Node — api_key Required

**Problem:** LLM node has no `api_key` field → fails unless env var is set.

**Change:** LLM node config requires `api_key` and `llm_provider`. Self-contained, no fallback.

```python
{
    "llm_provider": "openai",     # required
    "llm_model": "gpt-4o",       # required
    "api_key": "...",             # required, encrypted
    "system_prompt": "...",       # optional
    "temperature": 0.7,           # optional
    "max_tokens": 4096            # optional
}
```

**Affected files:** `app/workflows/nodes/executor.py`

### 2.3 Frontend — Agent Node in Workflow Editor

- Add `agent` to `NodePalette` with distinct icon
- `NodeInspector` for agent node: dropdown to select existing agent + toggle output mode (`text`/`structured`)
- Custom node component displaying agent name + avatar
- Agent list fetched via existing `GET /api/agents` endpoint

**Affected files:** `apps/frontend/src/features/workflows/components/`

---

## Phase 3: Security

### 3.1 Code Sandbox Service

**Problem:** `code_exec` tool runs user-supplied code via `subprocess.run` directly on host. No isolation.

**Solution:** Dedicated sandbox service running as a persistent container alongside postgres/redis.

**Structure:**

```
services/code-sandbox/
├── Dockerfile           # Multi-language: python + node + bash
├── docker-compose.yml
├── api/
│   ├── main.py          # Lightweight FastAPI
│   └── executor.py      # Subprocess runner with resource limits
└── requirements.txt
```

**API:**

```
POST /execute
{
    "code": "print('hello')",
    "language": "python",    # python | javascript | bash
    "timeout": 30
}

Response:
{
    "output": "hello\n",
    "exit_code": 0,
    "error": null,
    "execution_time_ms": 42
}
```

**Language support:**

```python
LANGUAGE_CONFIG = {
    "python":     {"command": ["python3", "/tmp/script.py"],  "ext": ".py"},
    "javascript": {"command": ["node", "/tmp/script.js"],     "ext": ".js"},
    "bash":       {"command": ["bash", "/tmp/script.sh"],     "ext": ".sh"},
}
```

**Isolation within container:**
- `ulimit` for memory/cpu per execution
- Timeout enforcement via subprocess
- No outbound network (docker-compose `internal: true` network)
- Non-root user inside container

**Backend integration:** `CodeExecToolBuilder` calls sandbox via HTTP:

```python
async def execute(**kwargs) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.post("http://code-sandbox:8000/execute", json={
            "code": code,
            "language": config.get("language", "python"),
            "timeout": tool_def.timeout_seconds,
        })
        return resp.json()["output"]
```

**docker-compose.yml (root):** Add `code-sandbox` service.

**Affected files:** `services/code-sandbox/` (new), `app/tools/registry.py`, `docker-compose.yml`

### 3.2 Condition Node — Safe Expression Parser

**Problem:** `eval()` with restricted `__builtins__` can still be escaped.

**Change:** Replace with `simpleeval` library.

```python
from simpleeval import simple_eval

result = simple_eval(
    expression,
    names={"data": input_data},
)
```

Only allows: comparisons, logic operators, attribute/key access, literals. Cannot call functions, import modules, or access dunder attributes.

**Affected files:** `app/workflows/nodes/executor.py`, `requirements.txt` (add `simpleeval`)

---

## Dependency Graph

```
Phase 1 (Chat Quality)          Phase 2 (Workflow)           Phase 3 (Security)
┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│ 1.1 Fix Retriever   │    │ 2.1 Agent Node       │    │ 3.1 Sandbox Service │
│ 1.2 KB Mode Config  │    │ 2.2 LLM Node api_key │    │ 3.2 Condition eval  │
│ 1.3 System Prompt   │    │ 2.3 Frontend         │    │                     │
└─────────────────────┘    └──────────────────────┘    └─────────────────────┘
        ▼                          ▼                           ▼
   All independent — can execute in parallel
```

Within each phase:
- Phase 1: 1.1 first (retriever), then 1.2 (depends on retriever), 1.3 independent
- Phase 2: 2.1 + 2.2 independent, 2.3 after 2.1 (frontend needs agent node API)
- Phase 3: 3.1 + 3.2 fully independent
