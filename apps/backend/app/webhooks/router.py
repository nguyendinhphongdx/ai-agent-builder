"""Public webhook endpoints.

Each active workflow with a ``webhook_trigger`` node exposes:
    POST /api/webhooks/{workflow_id}/{webhook_token}/{path:path}

The ``webhook_token`` is a per-workflow URL-embedded secret — leaking the
``workflow_id`` alone is not enough to fire the workflow. Owners can rotate
the token via ``POST /api/workflows/{id}/webhook-token/rotate``.

Response is driven by the node's ``config`` — see :func:`_build_response` for
the supported ``response_mode`` values.
"""

from __future__ import annotations

import logging
import secrets
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.db.session import get_db
from app.jobs import types as job_types
from app.jobs.producer import enqueue as enqueue_job
from app.models.workflow import Workflow
from app.models.workflow_node import WorkflowNode

logger = logging.getLogger("agentforge")

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _normalise_path(path: str) -> str:
    """Canonicalise a path for equality — always leading slash, no trailing slash."""
    if not path:
        return "/"
    path = "/" + path.lstrip("/")
    if len(path) > 1:
        path = path.rstrip("/")
    return path


def _find_matching_webhook_node(
    workflow: Workflow, path: str
) -> WorkflowNode | None:
    """Return the webhook_trigger node whose config path matches, if any."""
    target = _normalise_path(path)
    for node in workflow.nodes:
        if node.node_type != "webhook_trigger":
            continue
        configured = _normalise_path(str((node.config or {}).get("path", "")))
        if configured == target:
            return node
    return None


async def _build_input(request: Request) -> dict[str, Any]:
    """Shape the incoming request into the workflow's ``input_data`` dict."""
    body: Any
    try:
        body = await request.json()
    except Exception:
        try:
            form = await request.form()
            body = {k: v for k, v in form.items()}
        except Exception:
            raw = await request.body()
            body = raw.decode("utf-8", errors="replace") if raw else ""

    return {
        "body": body,
        "query": dict(request.query_params),
        "headers": {k.lower(): v for k, v in request.headers.items()},
        "method": request.method,
    }


def _build_response(
    config: dict[str, Any],
    run: Any | None,
) -> Response:
    """Translate the webhook node config + run outcome into an HTTP response.

    ``response_mode``:
    - ``"immediately"`` (default) — return ``response_data`` right away; workflow
      continues executing in the background.
    - ``"lastNode"`` — return the run's ``output_data`` verbatim.
    """
    response_code = int(config.get("response_code", 200))
    mode = config.get("response_mode", "immediately")

    if mode == "lastNode" and run is not None:
        return JSONResponse(
            status_code=response_code,
            content=getattr(run, "output_data", None),
        )

    # immediately (default) — fire-and-forget path
    data = config.get("response_data")
    if isinstance(data, (dict, list)):
        return JSONResponse(status_code=response_code, content=data)
    return JSONResponse(
        status_code=response_code,
        content={"ok": True, "message": data if data else "received"},
    )


# _run_detached previously executed workflows via `asyncio.create_task`.
# Replaced by `enqueue_job(JOB_WORKFLOW_RUN)` in the request handler —
# RabbitMQ-backed, persistent, retryable, surfaces in /admin/jobs.


@router.post("/{workflow_id}/{webhook_token}/{path:path}")
async def receive_webhook(
    workflow_id: uuid.UUID,
    webhook_token: str,
    path: str,
    request: Request,
):
    """Entry point for external callers to trigger an active workflow."""
    # Load workflow on a short-lived read session. Execution runs on its own
    # session (below) so the response can return before the workflow finishes.
    db_gen = get_db()
    db: AsyncSession = await anext(db_gen)
    try:
        result = await db.execute(
            select(Workflow)
            .options(selectinload(Workflow.nodes), selectinload(Workflow.edges))
            .where(Workflow.id == workflow_id)
        )
        workflow = result.scalar_one_or_none()
        if not workflow or not workflow.is_active:
            raise HTTPException(status_code=404, detail="Webhook not found")

        # Constant-time compare so a wrong-token caller can't time-side-channel
        # the right one. 404 (not 401) on mismatch keeps existence opaque.
        # Guard against legacy rows with NULL token — compare_digest raises
        # TypeError on None.
        if not workflow.webhook_token or not secrets.compare_digest(
            workflow.webhook_token, webhook_token
        ):
            raise HTTPException(status_code=404, detail="Webhook not found")

        trigger_node = _find_matching_webhook_node(workflow, path)
        if not trigger_node:
            raise HTTPException(status_code=404, detail="Webhook path not found")

        config = trigger_node.config or {}
        input_data = await _build_input(request)
        mode = config.get("response_mode", "immediately")

        if mode == "immediately":
            # Persistent fire-and-forget via the jobs queue. Earlier
            # this used asyncio.create_task; that worked but lost the
            # task on process restart and had no retry. Now it lands
            # in /admin/jobs and survives crashes.
            await enqueue_job(
                db,
                job_type=job_types.JOB_WORKFLOW_RUN,
                target="backend",
                path=f"{settings.API_PREFIX}/internal/workflows/run",
                payload={
                    "workflow_id": str(workflow.id),
                    "user_id": str(workflow.user_id),
                    "input_data": input_data,
                },
                workspace_id=workflow.workspace_id,
                user_id=workflow.user_id,
                priority="normal",
                retry={"maxAttempts": 3, "backoffMs": 5_000, "backoffMultiplier": 2},
                timeout_ms=300_000,
            )
            await db.commit()
            return _build_response(config, run=None)

        # lastNode: execute inline and return the final output.
        from app.workflows.runner import WorkflowRunner

        runner = WorkflowRunner(db)
        run = await runner.run(
            workflow=workflow,
            user_id=workflow.user_id,
            input_data=input_data,
        )
        return _build_response(config, run)
    finally:
        try:
            await db_gen.aclose()
        except Exception:
            pass
