"""Cron trigger node — passes the scheduler's payload through to
the rest of the graph.

The actual scheduling lives in ``app/scheduled_triggers/`` — this
executor only runs when the scheduler tick enqueues a workflow.run
job pointing at the workflow containing this node. The fire-time
payload sits in the request body, which the workflow runner makes
available to all trigger-class executors as ``items`` (single item
matching the trigger payload).
"""
from __future__ import annotations

from typing import Any

from ..base import ExecutionContext, NodeExecutor, NodeResult


class CronTriggerExecutor(NodeExecutor):
    """Pass-through trigger — input is whatever the scheduler sent."""

    async def execute(
        self,
        items: list[dict[str, Any]],
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> NodeResult:
        return NodeResult(items=items)
