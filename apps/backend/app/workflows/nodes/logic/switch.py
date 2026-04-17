from __future__ import annotations
from typing import Any
from ..base import ExecutionContext, NodeExecutor, NodeResult


class SwitchExecutor(NodeExecutor):
    """Routes items to the first matching case handle, or 'default_out'."""

    async def execute(self, items: list[dict[str, Any]], config: dict[str, Any], ctx: ExecutionContext) -> NodeResult:
        variable = config.get("variable", "")
        value = str(items[0].get(variable, "")) if items else ""
        cases: list[dict[str, Any]] = config.get("cases", [])
        for case in cases:
            if str(case.get("value", "")) == value:
                return NodeResult(items=items, route=str(case["id"]))
        return NodeResult(items=items, route="default_out")
