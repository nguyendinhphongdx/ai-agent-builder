from __future__ import annotations

import json
from typing import Any

from app.workflows.expression import evaluate_template

from ..base import ExecutionContext, NodeExecutor, NodeResult


class SetVariableExecutor(NodeExecutor):
    """Parse a JSON assignments map and write rendered values into ctx.variables.

    Each value is evaluated as an expression template, so a pure ``{{ expr }}``
    preserves type (e.g. ``42`` stays an int rather than ``"42"``).
    """

    async def execute(
        self,
        items: list[dict[str, Any]],
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> NodeResult:
        try:
            assignments: dict[str, Any] = json.loads(config.get("assignments", "{}"))
        except (json.JSONDecodeError, TypeError):
            assignments = {}

        source_item = items[0] if items else {}
        for key, expr in assignments.items():
            ctx.variables[key] = evaluate_template(
                str(expr),
                item=source_item,
                items=items,
                variables=ctx.variables,
                upstream=ctx.upstream_outputs,
            )

        return NodeResult(items=items)
