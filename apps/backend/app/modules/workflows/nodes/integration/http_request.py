from __future__ import annotations

import json
from typing import Any

import httpx

from app.modules.workflows.expression import evaluate_template

from ..base import ExecutionContext, NodeExecutor, NodeResult


class HTTPRequestExecutor(NodeExecutor):
    """Send an HTTP request for each incoming item and append the response."""

    async def execute(
        self,
        items: list[dict[str, Any]],
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> NodeResult:
        method = config.get("method", "GET").upper()
        url_template = config.get("url", "")
        headers_template = config.get("headers", "{}")
        body_template = config.get("body", "")
        timeout = float(config.get("timeout", 30))
        output_var = config.get("output_variable", "http_response")

        if not url_template:
            raise ValueError("url is required in http_request node config")

        def _render(template: str, item: dict[str, Any]) -> Any:
            return evaluate_template(
                template,
                item=item,
                items=items,
                variables=ctx.variables,
                upstream=ctx.upstream_outputs,
            )

        results: list[dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=timeout) as client:
            for item in items:
                url = str(_render(url_template, item))
                headers_rendered = _render(headers_template, item)
                if isinstance(headers_rendered, dict):
                    headers: dict[str, str] = {k: str(v) for k, v in headers_rendered.items()}
                else:
                    try:
                        headers = json.loads(str(headers_rendered))
                    except (json.JSONDecodeError, TypeError):
                        headers = {}
                body_rendered = _render(body_template, item) if body_template else None
                body = (
                    body_rendered
                    if isinstance(body_rendered, str) or body_rendered is None
                    else json.dumps(body_rendered)
                )

                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    content=body.encode() if body else None,
                )
                results.append(
                    {
                        **item,
                        output_var: {
                            "status": response.status_code,
                            "data": response.text,
                            "headers": dict(response.headers),
                        },
                    }
                )

        return NodeResult(items=results)
