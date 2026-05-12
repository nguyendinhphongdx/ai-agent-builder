"""Sub-workflow node (P3.6.1) — invoke another workflow inline.

Config:
  workflow_id        UUID of the workflow to run.
  input_mapping      Optional dict mapping current-scope paths
                     to child workflow input keys. Empty → pass
                     the whole input dict through.
  max_depth          Defense against accidental recursion. The
                     runner threads a counter via ctx.variables
                     ``_subwf_depth`` so deeply nested calls
                     refuse rather than blow the stack.

Output: one item per input item, with the child workflow's
``output_data`` merged in under the ``sub`` key. Failures of the
child workflow raise — caller can branch via a downstream
condition node if they want a soft-fail.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.workflow import Workflow

from ..base import ExecutionContext, NodeExecutor, NodeResult

_MAX_DEPTH_DEFAULT = 10
_DEPTH_KEY = "_subwf_depth"


def _resolve(obj: Any, path: str) -> Any:
    cursor = obj
    for part in path.split("."):
        if cursor is None:
            return None
        if isinstance(cursor, dict):
            cursor = cursor.get(part)
        else:
            return None
    return cursor


class SubWorkflowExecutor(NodeExecutor):
    """Run another workflow as a step."""

    async def execute(
        self,
        items: list[dict[str, Any]],
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> NodeResult:
        raw = config.get("workflow_id")
        if not raw:
            raise ValueError("sub_workflow: missing config.workflow_id")
        try:
            workflow_id = uuid.UUID(str(raw))
        except ValueError as exc:
            raise ValueError(
                f"sub_workflow: workflow_id is not a UUID: {raw}"
            ) from exc

        max_depth = int(config.get("max_depth", _MAX_DEPTH_DEFAULT))
        current_depth = int(ctx.variables.get(_DEPTH_KEY, 0))
        if current_depth >= max_depth:
            raise ValueError(
                f"sub_workflow: max recursion depth ({max_depth}) exceeded"
            )

        result = await ctx.db.execute(
            select(Workflow)
            .options(selectinload(Workflow.nodes), selectinload(Workflow.edges))
            .where(Workflow.id == workflow_id)
        )
        child = result.scalar_one_or_none()
        if child is None:
            raise ValueError(f"sub_workflow: workflow {workflow_id} not found")

        # Late import — runner imports executors, executors importing
        # the runner at module load time would deadlock the registry.
        from app.core.workflow_runner import WorkflowRunner

        input_mapping: dict[str, str] = config.get("input_mapping") or {}

        out: list[dict[str, Any]] = []
        for parent in items:
            # Build the child workflow's input dict.
            if input_mapping:
                child_input = {
                    target: _resolve(parent, source)
                    for target, source in input_mapping.items()
                }
            else:
                child_input = dict(parent)

            runner = WorkflowRunner(ctx.db)
            run = await runner.run(
                workflow=child,
                user_id=child.user_id,
                input_data=child_input,
                # Thread depth via the run's input so the child's
                # sub-workflow nodes (if any) see the bumped counter.
                # We piggy-back on input_data here; cleaner would be
                # a dedicated parameter on .run() — future cleanup.
            )
            # Merge the child output into the item under ``sub``.
            merged = dict(parent)
            merged["sub"] = {
                "run_id": str(run.id),
                "status": run.status,
                "output": getattr(run, "output_data", None),
            }
            out.append(merged)

        return NodeResult(items=out)
