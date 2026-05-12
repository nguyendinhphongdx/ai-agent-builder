from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.models.tool import Tool
from app.modules.studio.tools.registry import tool_registry

from ..base import ExecutionContext, NodeExecutor, NodeResult


class ToolExecutor(NodeExecutor):
    """Invoke a registered LangChain tool for each incoming item."""

    async def execute(self, items: list[dict[str, Any]], config: dict[str, Any], ctx: ExecutionContext) -> NodeResult:
        tool_id = config.get("tool_id")
        if not tool_id:
            raise ValueError("tool_id is required in tool node config")

        result = await ctx.db.execute(select(Tool).where(Tool.id == tool_id))
        tool_def = result.scalar_one_or_none()
        if not tool_def:
            raise ValueError(f"Tool not found: {tool_id}")

        lc_tool = tool_registry.build(tool_def)
        output_var = config.get("output_variable", "tool_result")

        results: list[dict[str, Any]] = []
        for item in items:
            tool_input: Any = item if isinstance(item, dict) else {"input": str(item)}
            tool_result = await lc_tool.ainvoke(tool_input)
            results.append({**item, output_var: tool_result})

        return NodeResult(items=results)
