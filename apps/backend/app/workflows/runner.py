"""Stack-based workflow execution engine.

Replaces LangGraph StateGraph with a custom runner that supports:
- Items-based data flow (list[dict] between nodes)
- N-way branching (condition, switch)
- Multi-output routing (filter → matched/unmatched)
- Merge waiting (wait for all inputs before executing)
- Per-node I/O tracking (for NDV frontend panels)
"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("agentforge")

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import Workflow
from app.workflows.nodes.base import (
    ExecutionContext,
    NodeExecution,
    NodeResult,
    RunResult,
    now_iso,
)
from app.workflows.nodes.registry import get_executor
from app.workflows.service import create_workflow_run, update_workflow_run
from app.workflows.socket_emitter import (
    emit_node_completed,
    emit_node_failed,
    emit_node_running,
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
        import time as _time

        from app.observability import tracing
        from app.observability.metrics import workflow_run_duration_seconds

        # Create run record
        run = await create_workflow_run(
            self.db, workflow.id, user_id, input_data, conversation_id
        )
        await self.db.commit()

        wf_id = str(workflow.id)
        run_id = str(run.id)
        _started = _time.perf_counter()

        # One OTEL span per workflow run with attributes the FE / ops
        # care about (id, name, node count). Nested node-level spans
        # come from each executor's own use of the helper.
        with tracing.span(
            "workflow.run",
            workflow_id=wf_id,
            run_id=run_id,
            workflow_name=workflow.name,
            node_count=len(workflow.nodes or []),
        ):
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
                await self._notify_terminal(workflow, run, result.status, result.error)

                workflow_run_duration_seconds.labels(status=result.status).observe(
                    _time.perf_counter() - _started
                )
            except Exception as e:
                tracing.record_exception(e)
                run = await update_workflow_run(
                    self.db,
                    run,
                    status="failed",
                    error_message=str(e),
                    completed_at=datetime.now(timezone.utc),
                )
                await self.db.commit()
                emit_workflow_failed(wf_id, run_id, str(e))
                await self._notify_terminal(workflow, run, "failed", str(e))
                workflow_run_duration_seconds.labels(status="failed").observe(
                    _time.perf_counter() - _started
                )

        return run

    async def _notify_terminal(
        self,
        workflow: Workflow,
        run: Any,
        status: str,
        error: str | None,
    ) -> None:
        """Persist an inbox notification for the workflow owner.

        Fire-and-forget pattern: never lets an inbox-write failure
        change the run outcome. Trigger-fired-from-cron runs notify
        the same owner — they want to know their automation broke
        even if they weren't watching.
        """
        try:
            from app.models.notification import (
                TYPE_WORKFLOW_FAILED,
                TYPE_WORKFLOW_SUCCEEDED,
            )
            from app.notifications import inbox as inbox_service

            if status == "completed":
                type_ = TYPE_WORKFLOW_SUCCEEDED
                title = f"Workflow “{workflow.name}” finished"
                body = None
            else:
                type_ = TYPE_WORKFLOW_FAILED
                title = f"Workflow “{workflow.name}” failed"
                body = (error or "Unknown error")[:500]

            await inbox_service.notify(
                self.db,
                user_id=workflow.user_id,
                type=type_,
                title=title,
                body=body,
                link_url=f"/workflows/{workflow.id}/runs/{run.id}",
                workspace_id=workflow.workspace_id,
                extra={"run_id": str(run.id), "status": status},
            )
            await self.db.commit()
        except Exception:  # noqa: BLE001 — telemetry-flavoured
            logger.debug("workflow notify failed", exc_info=True)

    async def run_single_node(
        self,
        workflow: Workflow,
        user_id: uuid.UUID,
        node_id: str,
        input_items: list[dict[str, Any]],
        config_overrides: dict[str, Any] | None = None,
    ) -> Any:
        """Execute a single node in isolation and persist as a partial run.

        Reuses the workflow_runs table so the regular history endpoints surface
        partial runs too — frontend filters by `is_partial` if needed.
        """
        node = next((n for n in workflow.nodes if str(n.id) == node_id), None)
        if node is None:
            raise ValueError(f"Node {node_id} not found in workflow")

        config = {**(node.config or {}), **(config_overrides or {})}

        # Hydrate upstream_outputs from the latest full run so expressions like
        # `{{ nodes["X"][0].field }}` resolve when the user clicks Execute Step
        # on a downstream node. Falls back to empty if no run history.
        upstream_outputs = await self._latest_upstream_outputs(workflow, node_id)

        run = await create_workflow_run(
            self.db,
            workflow.id,
            user_id,
            input_data={"input_items": input_items, "node_id": node_id},
            is_partial=True,
        )
        await self.db.commit()

        executor = get_executor(node.node_type)
        ctx = ExecutionContext(
            node_id=node_id,
            node_type=node.node_type,
            label=node.label,
            db=self.db,
            variables={},
            initial_input={},
            upstream_outputs=upstream_outputs,
        )

        started_at = now_iso()
        try:
            result = await executor.execute(input_items, config, ctx)
            execution = NodeExecution(
                node_id=node_id,
                node_type=node.node_type,
                label=node.label,
                status="completed",
                input_items=_safe_serialize(input_items),
                output_items=_safe_serialize(result.items),
                tokens_used=result.tokens_used,
                started_at=started_at,
                completed_at=now_iso(),
            )
            run = await update_workflow_run(
                self.db,
                run,
                status="completed",
                output_data=_safe_serialize(result.items),
                node_executions=[execution.to_dict()],
                total_tokens=result.tokens_used,
                completed_at=datetime.now(timezone.utc),
            )
        except Exception as e:
            execution = NodeExecution(
                node_id=node_id,
                node_type=node.node_type,
                label=node.label,
                status="failed",
                input_items=_safe_serialize(input_items),
                output_items=[],
                error=str(e),
                started_at=started_at,
                completed_at=now_iso(),
            )
            run = await update_workflow_run(
                self.db,
                run,
                status="failed",
                node_executions=[execution.to_dict()],
                error_message=str(e),
                completed_at=datetime.now(timezone.utc),
            )

        await self.db.commit()
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
            # Build upstream outputs map for expression context. Prefer node
            # label as key (what users see in the editor) and fall back to id
            # so unlabeled nodes are still addressable as `nodes["uuid"]`.
            upstream_outputs: dict[str, list[dict[str, Any]]] = {}
            for src_id, _handle in reverse_adj.get(node_id, []):
                src_result = node_results.get(src_id)
                if src_result is None:
                    continue
                src_node = node_map.get(src_id)
                key = (src_node.label if src_node and src_node.label else src_id)
                upstream_outputs[key] = src_result.items
                upstream_outputs[src_id] = src_result.items  # always also addressable by id

            executor = get_executor(node.node_type)
            ctx = ExecutionContext(
                node_id=node_id,
                node_type=node.node_type,
                label=node.label,
                db=self.db,
                variables=variables,
                initial_input=input_data if isinstance(input_data, dict) else {},
                upstream_outputs=upstream_outputs,
            )

            wf_id = str(workflow.id)
            started_at = now_iso()

            # Emit: node started
            emit_node_running(wf_id, node_id, node.node_type, node.label)

            try:
                # Disabled nodes pass-through input as output and emit a
                # `skipped` status. Lets users mute a node mid-flow without
                # rewiring edges (n8n behaviour).
                if (node.config or {}).get("disabled") is True:
                    node_executions.append(NodeExecution(
                        node_id=node_id,
                        node_type=node.node_type,
                        label=node.label,
                        status="skipped",
                        input_items=_safe_serialize(input_items),
                        output_items=_safe_serialize(input_items),
                        started_at=started_at,
                        completed_at=now_iso(),
                    ))
                    result = NodeResult(items=input_items)
                    node_results[node_id] = result
                    emit_node_completed(
                        wf_id, node_id, node.node_type, node.label,
                        output_items_count=len(input_items),
                        tokens_used=0,
                    )
                    # Route to next nodes with passthrough items.
                    targets = adjacency.get(node_id, [])
                    for target_id, _handle in targets:
                        stack.append((target_id, input_items))
                    continue

                # Pinned output short-circuit: skips the executor and reuses
                # frozen output captured by NDV "Pin". Lets users iterate on
                # downstream nodes without re-running expensive upstream
                # nodes (LLM calls, HTTP fetches).
                pinned = (node.config or {}).get("_pinned_output")
                if isinstance(pinned, list):
                    result = NodeResult(items=pinned)
                else:
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

    async def _latest_upstream_outputs(
        self, workflow: Workflow, node_id: str
    ) -> dict[str, list[dict[str, Any]]]:
        """Return upstream nodes' last-known output_items keyed by label and id.

        Used by ``run_single_node`` so Execute-Step expressions can reference
        ``nodes["X"]`` even though no real upstream is being executed. Empty
        dict when the workflow has never run.
        """
        from sqlalchemy import select as _select

        from app.models.workflow_run import WorkflowRun

        result = await self.db.execute(
            _select(WorkflowRun)
            .where(WorkflowRun.workflow_id == workflow.id)
            .order_by(WorkflowRun.started_at.desc())
            .limit(1)
        )
        latest = result.scalar_one_or_none()
        if latest is None or not latest.node_executions:
            return {}

        rev = self._build_reverse_adjacency(workflow.edges)
        ancestor_ids: set[str] = set()
        queue = [src for src, _h in rev.get(node_id, [])]
        while queue:
            current = queue.pop()
            if current in ancestor_ids:
                continue
            ancestor_ids.add(current)
            queue.extend(src for src, _h in rev.get(current, []))

        node_by_id = {str(n.id): n for n in workflow.nodes}
        outputs: dict[str, list[dict[str, Any]]] = {}
        for exec_log in latest.node_executions:
            nid = exec_log.get("node_id")
            if nid not in ancestor_ids:
                continue
            items = exec_log.get("output_items") or []
            outputs[nid] = items
            label = (node_by_id.get(nid).label if node_by_id.get(nid) else None)
            if label:
                outputs[label] = items
        return outputs


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
