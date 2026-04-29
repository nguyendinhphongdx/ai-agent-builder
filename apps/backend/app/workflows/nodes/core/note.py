from __future__ import annotations

from typing import Any

from ..base import ExecutionContext, NodeExecutor, NodeResult


class NoteExecutor(NodeExecutor):
    """No-op executor for sticky-note annotations.

    Notes never participate in execution — they have no handles, so the runner
    should never reach them. This executor exists only to satisfy
    ``get_executor`` lookups when a stale config does reach a note (e.g. legacy
    workflows that wired up a note before this restriction landed).
    """

    async def execute(
        self,
        items: list[dict[str, Any]],
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> NodeResult:
        return NodeResult(items=items)
