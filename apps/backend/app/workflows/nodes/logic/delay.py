from __future__ import annotations
import asyncio
from typing import Any
from ..base import ExecutionContext, NodeExecutor, NodeResult

_UNIT_MULTIPLIERS = {"seconds": 1, "minutes": 60, "hours": 3600}
_MAX_DELAY_SECONDS = 3600


class DelayExecutor(NodeExecutor):
    """Pauses execution for a configured duration (capped at 1 hour)."""

    async def execute(self, items: list[dict[str, Any]], config: dict[str, Any], ctx: ExecutionContext) -> NodeResult:
        amount: float = config.get("delay_seconds", 5)
        unit: str = config.get("unit", "seconds")
        multiplier = _UNIT_MULTIPLIERS.get(unit, 1)
        await asyncio.sleep(min(amount * multiplier, _MAX_DELAY_SECONDS))
        return NodeResult(items=items)
