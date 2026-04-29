from __future__ import annotations
from typing import Any
from app.workflows.expression import evaluate_template
from ..base import ExecutionContext, NodeExecutor, NodeResult


class TemplateExecutor(NodeExecutor):
    """Render a ``{{ expr }}`` template against each item.

    Each item is rendered with the full expression context (current ``json``,
    full ``items`` list, ``vars``, and ``nodes`` of upstream outputs). The
    rendered value is appended to the item under ``output_variable``.
    """

    async def execute(
        self,
        items: list[dict[str, Any]],
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> NodeResult:
        template: str = config.get("template", "")
        output_var: str = config.get("output_variable", "template_output")

        results: list[dict[str, Any]] = []
        for item in items:
            rendered = evaluate_template(
                template,
                item=item,
                items=items,
                variables=ctx.variables,
                upstream=ctx.upstream_outputs,
            )
            results.append({**item, output_var: rendered})

        return NodeResult(items=results)
