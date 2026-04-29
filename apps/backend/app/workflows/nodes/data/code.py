"""Code execution node — runs user-supplied code via the sandbox service.

The same pattern as :class:`app.tools.registry.CodeExecToolBuilder`: POST to
``settings.SANDBOX_URL/execute`` with a shared internal token. Sandbox is a
separate process (Docker container in dev) — never run user code in the
backend process.
"""
from __future__ import annotations
import json
from typing import Any

import httpx

from app.config import settings
from app.workflows.expression import evaluate_template
from ..base import ExecutionContext, NodeExecutor, NodeResult


class CodeExecutor(NodeExecutor):
    """Execute a code snippet against each input item via the sandbox service.

    Config:
    - ``code``: source string. Supports ``{{ json.x }}`` expression templates
      so authors can inject upstream values without hard-coding inputs.
    - ``language``: 'python' (default), 'javascript' — passed straight to sandbox.
    - ``output_variable``: where to attach the sandbox return value on each item
      (default 'code_result').
    - ``timeout``: seconds; capped at 60 by the sandbox itself.
    """

    async def execute(
        self,
        items: list[dict[str, Any]],
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> NodeResult:
        code_template: str = config.get("code", "")
        if not code_template.strip():
            raise ValueError("`code` is required in code node config")

        language = config.get("language", "python")
        output_var = config.get("output_variable", "code_result")
        timeout = float(config.get("timeout", 30))

        if not settings.SANDBOX_URL:
            raise ValueError(
                "SANDBOX_URL is not configured — refusing to execute user code "
                "in the backend process."
            )

        headers: dict[str, str] = {}
        if settings.SANDBOX_SECRET:
            headers["x-internal-token"] = settings.SANDBOX_SECRET

        # Per-item execution — each item gets its own context so templates
        # like ``{{ json.x }}`` resolve correctly when the upstream emitted
        # a list. Sandbox calls are kept sequential to bound concurrency
        # against the sandbox; switch to gather() if throughput becomes the
        # bottleneck.
        results: list[dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=timeout + 5) as client:
            for item in items or [{}]:
                rendered = evaluate_template(
                    code_template,
                    item=item,
                    items=items,
                    variables=ctx.variables,
                    upstream=ctx.upstream_outputs,
                )
                code = rendered if isinstance(rendered, str) else str(rendered)

                try:
                    resp = await client.post(
                        f"{settings.SANDBOX_URL}/execute",
                        json={
                            "code": code,
                            "language": language,
                            "timeout": int(timeout),
                        },
                        headers=headers,
                    )
                    resp.raise_for_status()
                    payload = resp.json()
                except httpx.HTTPError as exc:
                    raise RuntimeError(f"Sandbox request failed: {exc}") from exc

                # Sandbox response shape (matches CodeExecToolBuilder):
                #   { ok: bool, output: any, error: str|null, stderr: str|null }
                if payload.get("error"):
                    raise RuntimeError(f"Code error: {payload['error']}")

                results.append({**item, output_var: payload.get("output")})

        return NodeResult(items=results)


def _safe_dump(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(value)
