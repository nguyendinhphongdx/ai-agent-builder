from __future__ import annotations
from typing import Any
from ..base import ExecutionContext, NodeExecutor, NodeResult


class HumanInputExecutor(NodeExecutor):
    """Injects a value from the initial workflow input (or a default) into each item."""

    async def execute(self, items: list[dict[str, Any]], config: dict[str, Any], ctx: ExecutionContext) -> NodeResult:
        input_key: str = config.get("input_key", "human_input")
        default_value: Any = config.get("default_value", "")
        value = ctx.initial_input.get(input_key, default_value)
        base_item = items[0] if items else {}
        return NodeResult(items=[{**base_item, input_key: value}])
