from __future__ import annotations

from typing import Any

from simpleeval import simple_eval

from ..base import ExecutionContext, NodeExecutor, NodeResult


class FilterExecutor(NodeExecutor):
    """Splits items into 'matched' and 'unmatched' branches."""

    async def execute(self, items: list[dict[str, Any]], config: dict[str, Any], ctx: ExecutionContext) -> NodeResult:
        expression = config.get("expression", "True")
        matched: list[dict[str, Any]] = []
        unmatched: list[dict[str, Any]] = []
        for item in items:
            result = simple_eval(expression, names={"item": item, "vars": ctx.variables})
            (matched if result else unmatched).append(item)
        return NodeResult(items=matched, outputs={"matched": matched, "unmatched": unmatched})
