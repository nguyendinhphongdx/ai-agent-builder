from __future__ import annotations

from typing import Any

from ..base import ExecutionContext, NodeExecutor, NodeResult


class StartExecutor(NodeExecutor):
    """Entry point of a workflow. Passes initial items through unchanged."""

    async def execute(self, items: list[dict[str, Any]], config: dict[str, Any], ctx: ExecutionContext) -> NodeResult:
        return NodeResult(items=items)
