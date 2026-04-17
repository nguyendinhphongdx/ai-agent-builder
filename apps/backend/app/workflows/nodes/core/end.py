from __future__ import annotations
from typing import Any
from ..base import ExecutionContext, NodeExecutor, NodeResult


class EndExecutor(NodeExecutor):
    """Exit point of a workflow. Passes final items through unchanged."""

    async def execute(self, items: list[dict[str, Any]], config: dict[str, Any], ctx: ExecutionContext) -> NodeResult:
        return NodeResult(items=items)
