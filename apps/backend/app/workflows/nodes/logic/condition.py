from __future__ import annotations
from typing import Any
from simpleeval import simple_eval
from ..base import ExecutionContext, NodeExecutor, NodeResult


class ConditionExecutor(NodeExecutor):
    """Evaluates a boolean expression and routes to 'true' or 'false' handle."""

    async def execute(self, items: list[dict[str, Any]], config: dict[str, Any], ctx: ExecutionContext) -> NodeResult:
        expression = config.get("expression", "True")
        data = items[0] if items else {}
        result = simple_eval(expression, names={"data": data, "items": items, "vars": ctx.variables})
        return NodeResult(items=items, route="true" if result else "false")
