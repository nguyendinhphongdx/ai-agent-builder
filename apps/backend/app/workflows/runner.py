"""Stack-based workflow execution engine.

Replaces LangGraph StateGraph with a custom runner that supports:
- Items-based data flow (list[dict] between nodes)
- N-way branching (condition, switch)
- Multi-output routing (filter → matched/unmatched)
- Merge waiting (wait for all inputs before executing)
- Per-node I/O tracking (for NDV frontend panels)
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import Workflow
from app.workflows.nodes.base import (
    ExecutionContext,
    NodeExecution,
    RunResult,
    now_iso,
)
from app.workflows.nodes.registry import get_executor
from app.workflows.service import create_workflow_run, update_workflow_run
from app.workflows.socket_emitter import (
    emit_node_running,
    emit_node_completed,
    emit_node_failed,
    emit_workflow_completed,
    emit_workflow_failed,
)


class WorkflowRunner:
    """Stack-based workflow execution engine.

    Execution model (inspired by n8n):
    1. Push start node to stack with initial items
    2. Pop node → execute → push next nodes with output items
    3. Merge nodes wait until all inputs arrive
    4. Repeat until stack is empty
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def run(
        self,
        workflow: Workflow,
        user_id: uuid.UUID,
        input_data: dict[str, Any],
        conversation_id: uuid.UUID | None = None,
    ) -> Any:
        """Execute workflow and save results to WorkflowRun."""
        # Create run record
        run = await create_workflow_run(
            self.db, workflow.id, user_id, input_data, conversation_id
        )
        await self.db.commit()

        wf_id = str(workflow.id)
        run_id = str(run.id)

        try:
            result = await self._execute(workflow, input_data)

            run = await update_workflow_run(
                self.db,
                run,
                status=result.status,
                output_data=result.output,
                node_executions=[ne.to_dict() for ne in result.node_executions],
                total_tokens=result.total_tokens,
                error_message=result.error,
                completed_at=datetime.now(timezone.utc),
            )
            await self.db.commit()

            if result.status == "completed":
                emit_workflow_completed(wf_id, run_id, result.total_tokens)
            else:
                emit_workflow_failed(wf_id, run_id, result.error or "Unknown error")

        except Exception as e:
            run = await update_workflow_run(
                self.db,
                run,
                status="failed",
                error_message=str(e),
                completed_at=datetime.now(timezone.utc),
            )
            await self.db.commit()
            emit_workflow_failed(wf_id, run_id, str(e))

        return run

    async def _execute(
        self,
        workflow: Workflow,
        input_data: dict[str, Any],
    ) -> RunResult:
        """Core execution logic."""
        nodes = workflow.nodes
        edges = workflow.edges

        if not nodes:
            raise ValueError("Workflow has no nodes")

        # Build topology
        node_map = {str(n.id): n for n in nodes}
        adjacency = self._build_adjacency(edges)
        reverse_adj = self._build_reverse_adjacency(edges)
        start_id = self._find_start_node(nodes, edges)

        # Execution state
        node_results: dict[str, Any] = {}
        node_executions: list[NodeExecution] = []
        variables: dict[str, Any] = {}
        total_tokens: int = 0
        pending_merge: dict[str, dict[str, list[dict]]] = {}

        # Initial items
        initial_items = [input_data] if isinstance(input_data, dict) else [{"input": input_data}]

        # Stack: [(node_id, input_items)]
        stack: list[tuple[str, list[dict[str, Any]]]] = [(start_id, initial_items)]
        visited_count: dict[str, int] = defaultdict(int)

        while stack:
            node_id, input_items = stack.pop(0)
            node = node_map.get(node_id)
            if not node:
                continue

            # Safety: prevent infinite loops
            visited_count[node_id] += 1
            if visited_count[node_id] > 100:
                continue

            # --- Merge waiting ---
            incoming_edges = reverse_adj.get(node_id, [])
            if len(incoming_edges) > 1:
                if node_id not in pending_merge:
                    pending_merge[node_id] = {}

                source_key = f"input_{len(pending_merge[node_id])}"
                pending_merge[node_id][source_key] = input_items

                if len(pending_merge[node_id]) < len(incoming_edges):
                    continue  # Not all inputs ready

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

            wf_id = str(workflow.id)
            started_at = now_iso()

            # Emit: node started
            emit_node_running(wf_id, node_id, node.node_type, node.label)

            try:
                result = await executor.execute(
                    input_items, node.config or {}, ctx
                )
                node_results[node_id] = result
                total_tokens += result.tokens_used
                variables = ctx.variables

                node_executions.append(NodeExecution(
                    node_id=node_id,
                    node_type=node.node_type,
                    label=node.label,
                    status="completed",
                    input_items=_safe_serialize(input_items),
                    output_items=_safe_serialize(result.items),
                    tokens_used=result.tokens_used,
                    started_at=started_at,
                    completed_at=now_iso(),
                ))

                # Emit: node completed
                emit_node_completed(
                    wf_id, node_id, node.node_type, node.label,
                    output_items_count=len(result.items),
                    tokens_used=result.tokens_used,
                )

            except Exception as e:
                node_executions.append(NodeExecution(
                    node_id=node_id,
                    node_type=node.node_type,
                    label=node.label,
                    status="failed",
                    input_items=_safe_serialize(input_items),
                    output_items=[],
                    error=str(e),
                    started_at=started_at,
                    completed_at=now_iso(),
                ))

                # Emit: node failed
                emit_node_failed(wf_id, node_id, node.node_type, node.label, str(e))

                return RunResult(
                    status="failed",
                    output=None,
                    node_executions=node_executions,
                    total_tokens=total_tokens,
                    error=f"Node '{node.label or node.node_type}' failed: {e}",
                    variables=variables,
                )

            # --- Route to next nodes ---
            targets = adjacency.get(node_id, [])

            if result.route:
                # Conditional routing: follow matching handle only
                for target_id, handle in targets:
                    if handle == result.route:
                        stack.append((target_id, result.items))
                    elif handle is None and result.route == "default":
                        stack.append((target_id, result.items))

            elif result.outputs:
                # Multi-output: each handle gets different items
                for target_id, handle in targets:
                    handle_key = handle or "default"
                    if handle_key in result.outputs:
                        stack.append((target_id, result.outputs[handle_key]))

            else:
                # Normal: all targets get same items
                for target_id, _handle in targets:
                    stack.append((target_id, result.items))

        # Find final output from end/output node
        output = None
        for node in nodes:
            if node.node_type in ("end", "output"):
                nid = str(node.id)
                if nid in node_results:
                    output = node_results[nid].items

        return RunResult(
            status="completed",
            output=output,
            node_executions=node_executions,
            total_tokens=total_tokens,
            variables=variables,
        )

    # ─── Topology helpers ─────────────────────────────────────────

    @staticmethod
    def _build_adjacency(edges) -> dict[str, list[tuple[str, str | None]]]:
        adj: dict[str, list[tuple[str, str | None]]] = defaultdict(list)
        for e in edges:
            adj[str(e.source_node_id)].append((str(e.target_node_id), e.source_handle))
        return adj

    @staticmethod
    def _build_reverse_adjacency(edges) -> dict[str, list[tuple[str, str | None]]]:
        rev: dict[str, list[tuple[str, str | None]]] = defaultdict(list)
        for e in edges:
            rev[str(e.target_node_id)].append((str(e.source_node_id), e.target_handle))
        return rev

    @staticmethod
    def _find_start_node(nodes, edges) -> str:
        for n in nodes:
            if n.node_type in ("start", "input", "webhook_trigger"):
                return str(n.id)
        target_ids = {str(e.target_node_id) for e in edges}
        for n in nodes:
            if str(n.id) not in target_ids:
                return str(n.id)
        return str(nodes[0].id)


# ─── Helpers ──────────────────────────────────────────────────────

def _safe_serialize(items: list[dict[str, Any]], max_len: int = 1000) -> list[dict[str, Any]]:
    """Truncate large values for storage in node_executions JSONB."""
    result = []
    for item in items[:50]:  # Cap at 50 items
        safe_item = {}
        for key, value in item.items():
            s = str(value)
            safe_item[key] = s[:max_len] if len(s) > max_len else value
        result.append(safe_item)
    return result
