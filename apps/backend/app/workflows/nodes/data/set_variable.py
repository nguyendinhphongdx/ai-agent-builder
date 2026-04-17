from __future__ import annotations
import json
from typing import Any
from app.workflows.template_utils import render_template
from ..base import ExecutionContext, NodeExecutor, NodeResult


class SetVariableExecutor(NodeExecutor):
    """Parses a JSON assignments map and writes rendered values into ctx.variables."""

    async def execute(self, items: list[dict[str, Any]], config: dict[str, Any], ctx: ExecutionContext) -> NodeResult:
        try:
            assignments: dict[str, Any] = json.loads(config.get("assignments", "{}"))
        except (json.JSONDecodeError, TypeError):
            assignments = {}

        source_item = items[0] if items else {}
        for key, expr in assignments.items():
            ctx.variables[key] = render_template(str(expr), source_item)

        return NodeResult(items=items)
