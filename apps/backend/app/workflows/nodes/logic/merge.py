from __future__ import annotations
from typing import Any
from ..base import ExecutionContext, NodeExecutor, NodeResult


class MergeExecutor(NodeExecutor):
    """Passes through combined items; WorkflowRunner already merged multiple inputs."""

    async def execute(self, items: list[dict[str, Any]], config: dict[str, Any], ctx: ExecutionContext) -> NodeResult:
        # TODO: implement combine_position, combine_field, inner_join modes
        return NodeResult(items=items)
