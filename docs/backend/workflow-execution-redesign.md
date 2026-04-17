---
id: backend-workflow-execution-redesign
title: Workflow Execution Engine Redesign
domain: backend
tags: [workflows, execution, runner, nodes, state, redesign]
related: [frontend-workflow-editor-architecture-research]
summary: Custom stack-based workflow runner replacing LangGraph StateGraph. LangGraph only used inside Agent node for ReAct loops.
---

# Workflow Execution Engine Redesign

## 0. Architecture Decision

**We are building n8n**, not a LangGraph pipeline. LangGraph StateGraph is the wrong abstraction for workflow orchestration — it was designed for AI agent loops (ReAct), not general-purpose workflow execution with merge, N-way branching, loops, and per-node I/O tracking.

**Decision: Custom WorkflowRunner + LangGraph only inside Agent node.**

```
┌─────────────────────────────────────┐
│       WorkflowRunner (custom)       │  ← Stack-based, like n8n
│  Handles: routing, merge, loop,    │
│  per-node I/O, N-way branch        │
├─────────────────────────────────────┤
│  Node Executors (pure Python)       │
│  ├── Start/End        → passthrough │
│  ├── LLM              → LangChain  │
│  ├── Agent             → LangGraph │  ← ONLY place LangGraph is used
│  ├── HTTP Request      → httpx     │
│  ├── Tool              → tool_registry │
│  ├── Code              → sandbox   │
│  ├── Condition/Switch  → simpleeval │
│  ├── Filter            → simpleeval │
│  ├── Merge             → combine   │
│  ├── Loop              → iterator  │
│  ├── Delay             → asyncio   │
│  ├── Template          → render    │
│  ├── Set Variable      → assign    │
│  └── Knowledge Search  → pgvector  │
└─────────────────────────────────────┘
```

## 1. Data Model

### 1.1 Items (data unit flowing between nodes)

```python
# Every node receives and produces a list of items
# Each item is a dict (like a JSON object / DB row)
items: list[dict[str, Any]]

# Example:
[
    {"name": "Alice", "email": "alice@example.com", "score": 85},
    {"name": "Bob", "email": "bob@example.com", "score": 42},
]
```

### 1.2 NodeExecution (per-node tracking for NDV)

```python
@dataclass
class NodeExecution:
    node_id: str
    node_type: str
    label: str | None
    status: str                          # "completed" | "failed" | "skipped"
    input_items: list[dict[str, Any]]    # What went IN
    output_items: list[dict[str, Any]]   # What came OUT
    error: str | None
    tokens_used: int
    started_at: str                      # ISO datetime
    completed_at: str
```

### 1.3 RunResult (final output)

```python
@dataclass
class RunResult:
    status: str                          # "completed" | "failed"
    output: Any                          # Final workflow output
    node_executions: list[NodeExecution] # Per-node I/O (for NDV)
    total_tokens: int
    error: str | None
    variables: dict[str, Any]            # Final variable state
```

## 2. Node Executor Interface

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

@dataclass
class ExecutionContext:
    node_id: str
    node_type: str
    label: str | None
    db: AsyncSession
    variables: dict[str, Any]       # Shared variable space
    initial_input: dict             # Original workflow input

@dataclass
class NodeResult:
    """Result from a node execution."""
    items: list[dict[str, Any]]                         # Default output items
    route: str | None = None                            # For condition/switch: "true", "case_0", etc.
    outputs: dict[str, list[dict[str, Any]]] | None = None  # Multi-output: {"matched": [...], "unmatched": [...]}
    tokens_used: int = 0

class NodeExecutor(ABC):
    @abstractmethod
    async def execute(
        self,
        items: list[dict[str, Any]],
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> NodeResult:
        ...
```

**Key principle:** Executors are pure — they receive items, return items. No state mutation, no graph awareness.

## 3. WorkflowRunner (core engine)

```python
class WorkflowRunner:
    """Stack-based workflow execution engine.

    Execution model (like n8n):
    1. Push start node to stack
    2. Pop node from stack → execute → push next nodes
    3. Repeat until stack is empty
    4. Merge nodes wait until all inputs arrive
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def run(
        self,
        workflow: Workflow,
        input_data: dict,
        user_id: UUID,
    ) -> RunResult:
        # Build graph topology
        nodes, edges = workflow.nodes, workflow.edges
        node_map = {str(n.id): n for n in nodes}
        adjacency = self._build_adjacency(edges)
        reverse_adj = self._build_reverse_adjacency(edges)
        start_id = self._find_start_node(nodes, edges)

        # Execution state
        node_results: dict[str, NodeResult] = {}       # Per-node outputs
        node_executions: list[NodeExecution] = []       # Audit trail
        variables: dict[str, Any] = {}                  # Shared variables
        total_tokens: int = 0
        pending_merge: dict[str, dict[str, list]] = {}  # {node_id: {input_handle: items}}

        # Initial items
        initial_items = [input_data] if isinstance(input_data, dict) else [{"input": input_data}]

        # Stack: [(node_id, input_items)]
        stack: list[tuple[str, list[dict]]] = [(start_id, initial_items)]

        while stack:
            node_id, input_items = stack.pop(0)
            node = node_map.get(node_id)
            if not node:
                continue

            # --- Merge waiting ---
            incoming_edges = reverse_adj.get(node_id, [])
            if len(incoming_edges) > 1:
                # Multi-input node: wait for all inputs
                if node_id not in pending_merge:
                    pending_merge[node_id] = {}

                # Find which handle this input came from
                # (simplified: use source node id as key)
                source_key = f"input_{len(pending_merge[node_id])}"
                pending_merge[node_id][source_key] = input_items

                if len(pending_merge[node_id]) < len(incoming_edges):
                    continue  # Not all inputs ready yet

                # All inputs ready — combine
                input_items = []
                for items in pending_merge[node_id].values():
                    input_items.extend(items)
                del pending_merge[node_id]

            # --- Execute node ---
            executor = get_executor(node.node_type)
            ctx = ExecutionContext(
                node_id=node_id,
                node_type=node.node_type,
                label=node.label,
                db=self.db,
                variables=variables,
                initial_input=input_data if isinstance(input_data, dict) else {},
            )

            started_at = _now_iso()
            try:
                result = await executor.execute(input_items, node.config or {}, ctx)
                node_results[node_id] = result
                total_tokens += result.tokens_used
                variables = ctx.variables  # Executor may have modified variables

                node_executions.append(NodeExecution(
                    node_id=node_id,
                    node_type=node.node_type,
                    label=node.label,
                    status="completed",
                    input_items=input_items,
                    output_items=result.items,
                    error=None,
                    tokens_used=result.tokens_used,
                    started_at=started_at,
                    completed_at=_now_iso(),
                ))

            except Exception as e:
                node_executions.append(NodeExecution(
                    node_id=node_id,
                    node_type=node.node_type,
                    label=node.label,
                    status="failed",
                    input_items=input_items,
                    output_items=[],
                    error=str(e),
                    tokens_used=0,
                    started_at=started_at,
                    completed_at=_now_iso(),
                ))
                return RunResult(
                    status="failed",
                    output=None,
                    node_executions=node_executions,
                    total_tokens=total_tokens,
                    error=str(e),
                    variables=variables,
                )

            # --- Route to next nodes ---
            targets = adjacency.get(node_id, [])

            if result.route:
                # Conditional routing: only follow matching handle
                for target_id, handle in targets:
                    if handle == result.route or (handle is None and result.route == "default"):
                        stack.append((target_id, result.items))

            elif result.outputs:
                # Multi-output (filter): each handle gets different items
                for target_id, handle in targets:
                    handle_key = handle or "default"
                    if handle_key in result.outputs:
                        stack.append((target_id, result.outputs[handle_key]))

            else:
                # Normal: all targets get same items
                for target_id, _handle in targets:
                    stack.append((target_id, result.items))

        # Find output
        output = None
        for node in nodes:
            if node.node_type in ("end", "output"):
                end_result = node_results.get(str(node.id))
                if end_result:
                    output = end_result.items

        return RunResult(
            status="completed",
            output=output,
            node_executions=node_executions,
            total_tokens=total_tokens,
            error=None,
            variables=variables,
        )

    def _build_adjacency(self, edges):
        adj = defaultdict(list)
        for e in edges:
            adj[str(e.source_node_id)].append((str(e.target_node_id), e.source_handle))
        return adj

    def _build_reverse_adjacency(self, edges):
        rev = defaultdict(list)
        for e in edges:
            rev[str(e.target_node_id)].append((str(e.source_node_id), e.target_handle))
        return rev

    def _find_start_node(self, nodes, edges):
        for n in nodes:
            if n.node_type in ("start", "input", "webhook_trigger"):
                return str(n.id)
        target_ids = {str(e.target_node_id) for e in edges}
        for n in nodes:
            if str(n.id) not in target_ids:
                return str(n.id)
        return str(nodes[0].id)
```

## 4. Node Executors

### 4.1 Core

```python
class StartExecutor(NodeExecutor):
    async def execute(self, items, config, ctx):
        return NodeResult(items=items)

class EndExecutor(NodeExecutor):
    async def execute(self, items, config, ctx):
        return NodeResult(items=items)

class WebhookTriggerExecutor(NodeExecutor):
    async def execute(self, items, config, ctx):
        return NodeResult(items=items)
```

### 4.2 AI (LangChain + LangGraph)

```python
class LLMExecutor(NodeExecutor):
    async def execute(self, items, config, ctx):
        llm = build_llm(config)
        results = []
        total_tokens = 0
        output_var = config.get("output_variable", "response")

        for item in items:
            messages = []
            if config.get("system_prompt"):
                messages.append(SystemMessage(content=config["system_prompt"]))

            user_content = render_template(
                config.get("user_prompt_template", "{{input}}"), item
            )
            messages.append(HumanMessage(content=user_content))

            response = await llm.ainvoke(messages)
            total_tokens += extract_tokens(response)
            results.append({**item, output_var: response.content})

        return NodeResult(items=results, tokens_used=total_tokens)

class AgentExecutor(NodeExecutor):
    """The ONLY node that uses LangGraph internally."""
    async def execute(self, items, config, ctx):
        agent = await load_agent(ctx.db, config["agent_id"])
        llm = build_llm_from_agent(agent)
        tools = await build_agent_tools(agent, ctx.db)

        # LangGraph ReAct agent — this is what LangGraph is FOR
        graph = create_react_agent(llm, tools, prompt=agent.system_prompt)

        results = []
        total_tokens = 0
        for item in items:
            user_msg = str(item.get("input", item))
            result_state = await graph.ainvoke({"messages": [HumanMessage(content=user_msg)]})
            response = extract_final_response(result_state)
            results.append({**item, "response": response})

        return NodeResult(items=results, tokens_used=total_tokens)
```

### 4.3 Integration

```python
class HTTPRequestExecutor(NodeExecutor):
    async def execute(self, items, config, ctx):
        import httpx
        results = []
        output_var = config.get("output_variable", "http_response")

        async with httpx.AsyncClient(timeout=30) as client:
            for item in items:
                url = render_template(config.get("url", ""), item)
                headers = json.loads(render_template(config.get("headers", "{}"), item))
                body = render_template(config.get("body", ""), item)

                resp = await client.request(
                    method=config.get("method", "GET"),
                    url=url,
                    headers=headers,
                    content=body or None,
                )
                results.append({
                    **item,
                    output_var: {
                        "status": resp.status_code,
                        "data": resp.text,
                        "headers": dict(resp.headers),
                    },
                })
        return NodeResult(items=results)

class ToolExecutor(NodeExecutor):
    async def execute(self, items, config, ctx):
        tool_def = await load_tool(ctx.db, config["tool_id"])
        lc_tool = tool_registry.build(tool_def)
        output_var = config.get("output_variable", "tool_result")

        results = []
        for item in items:
            tool_input = item if isinstance(item, dict) else {"input": str(item)}
            result = await lc_tool.ainvoke(tool_input)
            results.append({**item, output_var: result})
        return NodeResult(items=results)
```

### 4.4 Data

```python
class TemplateExecutor(NodeExecutor):
    async def execute(self, items, config, ctx):
        template = config.get("template", "")
        output_var = config.get("output_variable", "template_output")
        return NodeResult(
            items=[{**item, output_var: render_template(template, item)} for item in items]
        )

class SetVariableExecutor(NodeExecutor):
    async def execute(self, items, config, ctx):
        assignments = json.loads(config.get("assignments", "{}"))
        for key, expr in assignments.items():
            ctx.variables[key] = render_template(str(expr), items[0] if items else {})
        return NodeResult(items=items)

class CodeExecutor(NodeExecutor):
    async def execute(self, items, config, ctx):
        code = config.get("code", "")
        language = config.get("language", "python")
        output_var = config.get("output_variable", "code_result")
        result = await run_sandboxed(code, {"items": items, "variables": ctx.variables}, language)
        return NodeResult(items=[{**items[0], output_var: result}] if items else [])

class KnowledgeRetrievalExecutor(NodeExecutor):
    async def execute(self, items, config, ctx):
        query = render_template(config.get("query_template", "{{input}}"), items[0] if items else {})
        top_k = config.get("top_k", 5)
        results = await search_knowledge_base(ctx.db, query, top_k)
        output_var = config.get("output_variable", "retrieved_context")
        return NodeResult(items=[{**(items[0] if items else {}), output_var: results}])
```

### 4.5 Logic

```python
class ConditionExecutor(NodeExecutor):
    async def execute(self, items, config, ctx):
        expression = config.get("expression", "True")
        data = items[0] if items else {}
        result = simple_eval(expression, names={"data": data, "items": items, "vars": ctx.variables})
        return NodeResult(items=items, route="true" if result else "false")

class SwitchExecutor(NodeExecutor):
    async def execute(self, items, config, ctx):
        variable = config.get("variable", "")
        value = str(items[0].get(variable, "")) if items else ""
        cases = config.get("cases", [])
        for case in cases:
            if str(case.get("value", "")) == value:
                return NodeResult(items=items, route=case["id"])
        return NodeResult(items=items, route="default_out")

class FilterExecutor(NodeExecutor):
    async def execute(self, items, config, ctx):
        expression = config.get("expression", "True")
        matched, unmatched = [], []
        for item in items:
            result = simple_eval(expression, names={"item": item, "vars": ctx.variables})
            (matched if result else unmatched).append(item)
        return NodeResult(
            items=matched,
            outputs={"matched": matched, "unmatched": unmatched},
        )

class MergeExecutor(NodeExecutor):
    async def execute(self, items, config, ctx):
        # Items already combined by WorkflowRunner's merge logic
        mode = config.get("mode", "append")
        if mode == "append":
            return NodeResult(items=items)
        # TODO: combine_position, combine_field, inner_join
        return NodeResult(items=items)

class LoopExecutor(NodeExecutor):
    async def execute(self, items, config, ctx):
        batch_size = config.get("batch_size", 1)
        max_iter = config.get("max_iterations", 100)
        # Runner handles iteration externally
        # This just passes items through
        return NodeResult(items=items)

class DelayExecutor(NodeExecutor):
    async def execute(self, items, config, ctx):
        import asyncio
        seconds = config.get("delay_seconds", 5)
        unit = config.get("unit", "seconds")
        multiplier = {"seconds": 1, "minutes": 60, "hours": 3600}.get(unit, 1)
        await asyncio.sleep(min(seconds * multiplier, 3600))  # Cap at 1 hour
        return NodeResult(items=items)

class HumanInputExecutor(NodeExecutor):
    async def execute(self, items, config, ctx):
        input_key = config.get("input_key", "human_input")
        default_value = config.get("default_value", "")
        value = ctx.initial_input.get(input_key, default_value)
        return NodeResult(items=[{**(items[0] if items else {}), input_key: value}])
```

### 4.6 Executor Registry

```python
EXECUTORS: dict[str, NodeExecutor] = {
    "start": StartExecutor(),
    "input": StartExecutor(),
    "end": EndExecutor(),
    "output": EndExecutor(),
    "webhook_trigger": WebhookTriggerExecutor(),
    "llm": LLMExecutor(),
    "agent": AgentExecutor(),
    "tool": ToolExecutor(),
    "http_request": HTTPRequestExecutor(),
    "condition": ConditionExecutor(),
    "switch": SwitchExecutor(),
    "filter": FilterExecutor(),
    "merge": MergeExecutor(),
    "loop": LoopExecutor(),
    "delay": DelayExecutor(),
    "template": TemplateExecutor(),
    "set_variable": SetVariableExecutor(),
    "code": CodeExecutor(),
    "knowledge_retrieval": KnowledgeRetrievalExecutor(),
    "human_input": HumanInputExecutor(),
}

def get_executor(node_type: str) -> NodeExecutor:
    executor = EXECUTORS.get(node_type)
    if not executor:
        raise ValueError(f"Unknown node type: {node_type}")
    return executor
```

## 5. Template Rendering

```python
import re

def render_template(template: str, data: dict[str, Any]) -> str:
    """Replace {{key}} and {{key.nested}} with values from data."""
    def replacer(match):
        path = match.group(1).strip()
        value = data
        for key in path.split("."):
            if isinstance(value, dict):
                value = value.get(key, "")
            else:
                return ""
        return str(value)
    return re.sub(r"\{\{(.+?)\}\}", replacer, template)
```

## 6. NDV API (per-node I/O)

```python
# GET /workflows/{id}/runs/{run_id}/nodes/{node_id}
@router.get("/{workflow_id}/runs/{run_id}/nodes/{node_id}")
async def get_node_execution(workflow_id, run_id, node_id, db):
    run = await get_workflow_run(db, run_id)
    node_exec = next(
        (n for n in run.node_executions if n["node_id"] == node_id),
        None,
    )
    if not node_exec:
        raise HTTPException(404)
    return node_exec
    # Returns: { input_items, output_items, status, tokens_used, ... }
```

Frontend NDV panels:
- **Schema**: derive from `items[0]` keys → `{ key: typeof value }`
- **Table**: items as rows, keys as columns
- **JSON**: raw JSON with highlight

## 7. Migration Plan

### Phase 1: WorkflowRunner + NodeExecutor base
- Create `runner.py` with `WorkflowRunner` class
- Create `base.py` with `NodeExecutor`, `NodeResult`, `ExecutionContext`
- Create `template_utils.py` with `render_template()`
- Update `compile_and_run()` to use `WorkflowRunner` instead of LangGraph StateGraph
- Remove `compiler.py` StateGraph code

### Phase 2: Migrate existing executors
- Convert function-based executors to class-based
- Start, End, LLM, Tool, Condition, HumanInput, Agent
- Keep Agent using LangGraph internally

### Phase 3: New executors
- HTTPRequest, Template, SetVariable, Delay
- Switch, Filter, Merge
- Code (sandbox), KnowledgeRetrieval

### Phase 4: NDV API
- New endpoint `/runs/{run_id}/nodes/{node_id}`
- Frontend Input/Output panels fetch per-node data
- Schema / Table / JSON views

## 8. File Structure

```
app/workflows/
├── runner.py                    # WorkflowRunner (replaces compiler.py)
├── compiler.py                  # DELETED — replaced by runner.py
├── router.py                    # API endpoints (add NDV endpoint)
├── schemas.py                   # Pydantic models (add NodeExecution)
├── service.py                   # DB CRUD
├── template_utils.py            # render_template()
└── nodes/
    ├── base.py                  # NodeExecutor, NodeResult, ExecutionContext
    ├── registry.py              # EXECUTORS dict + get_executor()
    ├── core.py                  # Start, End, WebhookTrigger
    ├── ai.py                    # LLM, Agent
    ├── integration.py           # HTTPRequest, Tool
    ├── data.py                  # Template, SetVariable, Code, KnowledgeRetrieval
    └── logic.py                 # Condition, Switch, Filter, Merge, Loop, Delay, HumanInput
```
