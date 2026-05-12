"""Code execution node — runs user-supplied code via the sandbox service.

Routed through the dispatcher (which owns the ``code-sandbox`` target
in its routes.json + queue-resolver), so target URL + auth headers
are managed in one place. Same pattern as
:class:`app.modules.studio.tools.registry.CodeExecToolBuilder`.
"""
from __future__ import annotations

import json
from typing import Any

from app.modules.studio.workflows.expression import evaluate_template
from app.platform.dispatcher_client import dispatcher

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

        # Per-item execution — each item gets its own context so templates
        # like ``{{ json.x }}`` resolve correctly when the upstream emitted
        # a list. Sandbox calls are kept sequential to bound concurrency
        # against the sandbox; switch to gather() if throughput becomes the
        # bottleneck.
        results: list[dict[str, Any]] = []
        for item in items or [{}]:
            rendered = evaluate_template(
                code_template,
                item=item,
                items=items,
                variables=ctx.variables,
                upstream=ctx.upstream_outputs,
            )
            code = rendered if isinstance(rendered, str) else str(rendered)

            resp = await dispatcher.call(
                target="code-sandbox",
                path="/execute",
                method="POST",
                body={
                    "code": code,
                    "language": language,
                    "timeout": int(timeout),
                },
                timeout=timeout + 5,
            )
            if resp.get("status", 500) >= 400:
                raise RuntimeError(
                    f"Sandbox request failed: {resp.get('status')} {resp.get('data')}"
                )
            # Sandbox response shape:
            #   { ok: bool, output: any, error: str|null, stderr: str|null }
            payload = resp.get("data") or {}
            if payload.get("error"):
                raise RuntimeError(f"Code error: {payload['error']}")

            results.append({**item, output_var: payload.get("output")})

        return NodeResult(items=results)


def _safe_dump(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(value)
