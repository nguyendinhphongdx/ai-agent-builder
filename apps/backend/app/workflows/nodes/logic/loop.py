from __future__ import annotations
from typing import Any
from ..base import ExecutionContext, NodeExecutor, NodeResult


class LoopExecutor(NodeExecutor):
    """Passthrough node; WorkflowRunner handles iteration externally."""

    async def execute(self, items: list[dict[str, Any]], config: dict[str, Any], ctx: ExecutionContext) -> NodeResult:
        return NodeResult(items=items)
