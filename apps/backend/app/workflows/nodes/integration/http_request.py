from __future__ import annotations
import json
from typing import Any
import httpx
from app.workflows.template_utils import render_template
from ..base import ExecutionContext, NodeExecutor, NodeResult


class HTTPRequestExecutor(NodeExecutor):
    """Send an HTTP request for each incoming item and append the response."""

    async def execute(self, items: list[dict[str, Any]], config: dict[str, Any], ctx: ExecutionContext) -> NodeResult:
        method = config.get("method", "GET").upper()
        url_template = config.get("url", "")
        headers_template = config.get("headers", "{}")
        body_template = config.get("body", "")
        timeout = float(config.get("timeout", 30))
        output_var = config.get("output_variable", "http_response")

        if not url_template:
            raise ValueError("url is required in http_request node config")

        results: list[dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=timeout) as client:
            for item in items:
                url = render_template(url_template, item)
                try:
                    headers: dict[str, str] = json.loads(render_template(headers_template, item))
                except json.JSONDecodeError:
                    headers = {}
                body = render_template(body_template, item) if body_template else None

                response = await client.request(method=method, url=url, headers=headers, content=body.encode() if body else None)
                results.append({**item, output_var: {"status": response.status_code, "data": response.text, "headers": dict(response.headers)}})

        return NodeResult(items=results)
