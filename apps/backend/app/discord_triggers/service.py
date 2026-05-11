"""Discord trigger CRUD + Ed25519 verification + dispatch.

Discord interactions are signed:
  base = X-Signature-Timestamp + raw_body
  Ed25519 verify(public_key, signature, base)

The public key is shown in the Discord developer portal and is NOT
secret. We store it per-trigger so a deployment with several
Discord bots doesn't have to share keys.

Replay window: Discord docs don't mandate one. We apply a 5-minute
clock check ourselves to keep cached payload abuse small.

Spec: https://discord.com/developers/docs/interactions/receiving-and-responding
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Sequence

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.context import current_workspace_id_or_none
from app.jobs import types as job_types
from app.jobs.producer import enqueue as enqueue_job
from app.models.discord_trigger import DiscordTrigger
from app.models.workflow import Workflow

logger = logging.getLogger("agentforge")

# Match what Slack uses by default — 5 min replay window.
_REPLAY_WINDOW_SECONDS = 300


# ─── CRUD ──────────────────────────────────────────────────────────


async def list_triggers(
    db: AsyncSession, workflow_id: uuid.UUID | None = None
) -> Sequence[DiscordTrigger]:
    workspace_id = current_workspace_id_or_none()
    stmt = select(DiscordTrigger).order_by(DiscordTrigger.created_at.desc())
    if workspace_id is not None:
        stmt = stmt.where(DiscordTrigger.workspace_id == workspace_id)
    if workflow_id is not None:
        stmt = stmt.where(DiscordTrigger.workflow_id == workflow_id)
    return (await db.execute(stmt)).scalars().all()


async def get_trigger(
    db: AsyncSession, trigger_id: uuid.UUID
) -> DiscordTrigger | None:
    workspace_id = current_workspace_id_or_none()
    stmt = select(DiscordTrigger).where(DiscordTrigger.id == trigger_id)
    if workspace_id is not None:
        stmt = stmt.where(DiscordTrigger.workspace_id == workspace_id)
    return await db.scalar(stmt)


async def create_trigger(
    db: AsyncSession,
    *,
    workflow_id: uuid.UUID,
    name: str,
    discord_application_id: str,
    discord_public_key: str,
    filter_command: str | None = None,
    is_active: bool = True,
) -> DiscordTrigger:
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
    row = DiscordTrigger(
        workflow_id=workflow_id,
        workspace_id=workspace_id,
        name=name,
        discord_application_id=discord_application_id,
        discord_public_key=discord_public_key.lower(),
        filter_command=filter_command,
        is_active=is_active,
    )
    db.add(row)
    await db.flush()
    return row


async def delete_trigger(db: AsyncSession, trigger: DiscordTrigger) -> None:
    await db.delete(trigger)
    await db.flush()


# ─── Signature verification ────────────────────────────────────────


def verify_signature(
    *,
    public_key_hex: str,
    raw_body: bytes,
    signature_hex: str | None,
    timestamp: str | None,
    now: float | None = None,
) -> None:
    """Raises HTTPException(401) on any Ed25519 verification failure."""
    if not signature_hex or not timestamp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "missing_signature", "detail": "X-Signature-* headers required"},
        )
    # Replay window — cheap check before the asymmetric crypto.
    try:
        ts_int = int(timestamp)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "bad_timestamp_format", "detail": "Timestamp must be an integer"},
        ) from None
    current = now if now is not None else time.time()
    if abs(current - ts_int) > _REPLAY_WINDOW_SECONDS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "stale_timestamp", "detail": "Timestamp outside replay window"},
        )

    try:
        key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
        key.verify(
            bytes.fromhex(signature_hex),
            timestamp.encode() + raw_body,
        )
    except (InvalidSignature, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "signature_mismatch", "detail": "Ed25519 verification failed"},
        ) from exc


# ─── Dispatch ──────────────────────────────────────────────────────


def _command_name(interaction: dict[str, Any]) -> str | None:
    """Extract the slash command name from an interaction payload."""
    data = interaction.get("data") or {}
    return data.get("name")


async def dispatch_interaction(
    db: AsyncSession,
    *,
    application_id: str,
    interaction: dict[str, Any],
) -> int:
    """Find matching active Discord triggers and enqueue runs.

    Index ``ix_discord_triggers_app`` covers the lookup.
    """
    rows = (
        await db.execute(
            select(DiscordTrigger).where(
                DiscordTrigger.discord_application_id == application_id,
                DiscordTrigger.is_active.is_(True),
            )
        )
    ).scalars().all()

    cmd = _command_name(interaction)
    dispatched = 0
    for trigger in rows:
        if trigger.filter_command and trigger.filter_command != cmd:
            continue
        workflow = await db.get(Workflow, trigger.workflow_id)
        if workflow is None or not workflow.is_active:
            continue
        await enqueue_job(
            db,
            job_type=job_types.JOB_WORKFLOW_RUN,
            target="backend",
            path=f"{settings.API_PREFIX}/internal/workflows/run",
            payload={
                "workflow_id": str(workflow.id),
                "user_id": str(workflow.user_id),
                "input_data": {
                    "trigger": "discord",
                    "trigger_id": str(trigger.id),
                    "discord": interaction,
                },
            },
            workspace_id=workflow.workspace_id,
            user_id=workflow.user_id,
            priority="normal",
            retry={"maxAttempts": 3, "backoffMs": 5_000, "backoffMultiplier": 2},
            timeout_ms=300_000,
        )
        dispatched += 1
    return dispatched
