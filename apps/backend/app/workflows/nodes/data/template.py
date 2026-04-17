from __future__ import annotations
from typing import Any
from app.workflows.template_utils import render_template
from ..base import ExecutionContext, NodeExecutor, NodeResult


class TemplateExecutor(NodeExecutor):
    """Renders a {{key}} template against each item."""

    async def execute(self, items: list[dict[str, Any]], config: dict[str, Any], ctx: ExecutionContext) -> NodeResult:
        template: str = config.get("template", "")
        output_var: str = config.get("output_variable", "template_output")
        return NodeResult(items=[{**item, output_var: render_template(template, item)} for item in items])
