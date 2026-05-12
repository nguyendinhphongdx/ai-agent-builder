"""Teams trigger CRUD + signature verification + dispatch.

Teams outgoing webhook signature spec:
  Header: ``Authorization: HMAC <base64_hmac_sha256>``
  HMAC body: raw request body bytes
  Key: base64-decoded shared secret Teams shows once at webhook
       creation time. We store it base64-encoded (encrypted).

Spec:
  https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/add-outgoing-webhook
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import uuid
from typing import Any, Sequence

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.teams_trigger import TeamsTrigger
from app.models.workflow import Workflow
from app.modules.jobs import types as job_types
from app.modules.jobs.producer import enqueue as enqueue_job
from app.platform.config import settings
from app.platform.context import current_workspace_id_or_none
from app.platform.security.crypto import decrypt_secret, encrypt_secret

logger = logging.getLogger("agentforge")


# ─── CRUD ──────────────────────────────────────────────────────────


async def list_triggers(
    db: AsyncSession, workflow_id: uuid.UUID | None = None
) -> Sequence[TeamsTrigger]:
    workspace_id = current_workspace_id_or_none()
    stmt = select(TeamsTrigger).order_by(TeamsTrigger.created_at.desc())
    if workspace_id is not None:
        stmt = stmt.where(TeamsTrigger.workspace_id == workspace_id)
    if workflow_id is not None:
        stmt = stmt.where(TeamsTrigger.workflow_id == workflow_id)
    return (await db.execute(stmt)).scalars().all()


async def get_trigger(
    db: AsyncSession, trigger_id: uuid.UUID
) -> TeamsTrigger | None:
    workspace_id = current_workspace_id_or_none()
    stmt = select(TeamsTrigger).where(TeamsTrigger.id == trigger_id)
    if workspace_id is not None:
        stmt = stmt.where(TeamsTrigger.workspace_id == workspace_id)
    return await db.scalar(stmt)


async def create_trigger(
    db: AsyncSession,
    *,
    workflow_id: uuid.UUID,
    name: str,
    hmac_secret: str,
    filter_keyword: str | None = None,
    is_active: bool = True,
) -> TeamsTrigger:
    workspace_id = current_workspace_id_or_none()
    if workspace_id is None:
        raise ValueError("no_active_workspace")
    wf = await db.scalar(
        select(Workflow).where(
            Workflow.id == workflow_id,
            Workflow.workspace_id == workspace_id,
        )
    )
    if wf is None:
        raise ValueError("workflow_not_found")
    row = TeamsTrigger(
        workflow_id=workflow_id,
        workspace_id=workspace_id,
        name=name,
        hmac_secret_enc=encrypt_secret(hmac_secret),
        filter_keyword=filter_keyword,
        is_active=is_active,
    )
    db.add(row)
    await db.flush()
    return row


async def delete_trigger(db: AsyncSession, trigger: TeamsTrigger) -> None:
    await db.delete(trigger)
    await db.flush()


# ─── Signature verification ────────────────────────────────────────


def _verify_signature(
    trigger: TeamsTrigger, raw_body: bytes, auth_header: str | None
) -> None:
    """Teams sends ``Authorization: HMAC <base64sig>``. Verify
    constant-time against the per-trigger secret.

    Raises HTTPException(401) on any failure.
    """
    if not auth_header or not auth_header.startswith("HMAC "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "missing_signature", "detail": "Authorization HMAC required"},
        )
    provided_b64 = auth_header[len("HMAC ") :].strip()

    try:
        secret_b64 = decrypt_secret(trigger.hmac_secret_enc)
        secret_bytes = base64.b64decode(secret_b64)
    except Exception as exc:  # noqa: BLE001
        logger.exception("teams trigger %s: bad secret", trigger.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "bad_secret", "detail": "Trigger secret is malformed"},
        ) from exc

    expected_bytes = hmac.new(secret_bytes, raw_body, hashlib.sha256).digest()
    expected_b64 = base64.b64encode(expected_bytes).decode()
    if not hmac.compare_digest(expected_b64, provided_b64):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "signature_mismatch", "detail": "HMAC does not match body"},
        )


# ─── Dispatch ──────────────────────────────────────────────────────


async def dispatch_event(
    db: AsyncSession,
    trigger: TeamsTrigger,
    *,
    raw_body: bytes,
    auth_header: str | None,
    payload: dict[str, Any],
) -> bool:
    """Verify the signature, apply keyword filter, enqueue a run.

    Returns True iff the workflow was enqueued.
    """
    _verify_signature(trigger, raw_body, auth_header)

    text = (payload.get("text") or "") if isinstance(payload, dict) else ""
    if trigger.filter_keyword and trigger.filter_keyword.lower() not in text.lower():
        return False

    workflow = await db.get(Workflow, trigger.workflow_id)
    if workflow is None or not workflow.is_active:
        return False
    await enqueue_job(
        db,
        job_type=job_types.JOB_WORKFLOW_RUN,
        target="backend",
        path=f"{settings.API_PREFIX}/internal/workflows/run",
        payload={
            "workflow_id": str(workflow.id),
            "user_id": str(workflow.user_id),
            "input_data": {
                "trigger": "teams",
                "trigger_id": str(trigger.id),
                "teams": payload,
            },
        },
        workspace_id=workflow.workspace_id,
        user_id=workflow.user_id,
        priority="normal",
        retry={"maxAttempts": 3, "backoffMs": 5_000, "backoffMultiplier": 2},
        timeout_ms=300_000,
    )
    return True
