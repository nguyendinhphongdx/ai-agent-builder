"""Public webhook endpoints.

Each active workflow with a ``webhook_trigger`` node exposes:
    POST /api/webhooks/{workflow_id}/{path:path}

Response is driven by the node's ``config`` — see :func:`_build_response` for
the supported ``response_mode`` values.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import async_session_factory, get_db
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


async def _run_detached(
    workflow_id: uuid.UUID,
    user_id: uuid.UUID,
    input_data: dict[str, Any],
) -> None:
    """Execute the workflow on a fresh DB session — used by `immediately` mode."""
    try:
        async with async_session_factory() as db:
            result = await db.execute(
                select(Workflow)
                .options(selectinload(Workflow.nodes), selectinload(Workflow.edges))
                .where(Workflow.id == workflow_id)
            )
            workflow = result.scalar_one_or_none()
            if not workflow:
                return

            from app.workflows.runner import WorkflowRunner

            runner = WorkflowRunner(db)
            await runner.run(
                workflow=workflow,
                user_id=user_id,
                input_data=input_data,
            )
            await db.commit()
    except Exception:
        logger.exception("Background webhook execution failed")


@router.post("/{workflow_id}/{path:path}")
async def receive_webhook(
    workflow_id: uuid.UUID,
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

        trigger_node = _find_matching_webhook_node(workflow, path)
        if not trigger_node:
            raise HTTPException(status_code=404, detail="Webhook path not found")

        config = trigger_node.config or {}
        input_data = await _build_input(request)
        mode = config.get("response_mode", "immediately")

        if mode == "immediately":
            # Fire-and-forget: start execution on a fresh session and respond now.
            asyncio.create_task(
                _run_detached(workflow.id, workflow.user_id, input_data)
            )
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
