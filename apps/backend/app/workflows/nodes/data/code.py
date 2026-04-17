from __future__ import annotations
from typing import Any
from ..base import ExecutionContext, NodeExecutor, NodeResult


class CodeExecutor(NodeExecutor):
    """Stub executor for user-supplied code.

    TODO: integrate a sandboxed execution environment (RestrictedPython or subprocess).
    """

    async def execute(self, items: list[dict[str, Any]], config: dict[str, Any], ctx: ExecutionContext) -> NodeResult:
        return NodeResult(items=items)
