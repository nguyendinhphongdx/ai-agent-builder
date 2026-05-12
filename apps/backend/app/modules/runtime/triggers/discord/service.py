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
import uuid
from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.discord_trigger import DiscordTrigger
from app.models.workflow import Workflow
from app.modules.runtime.jobs import types as job_types
from app.modules.runtime.jobs.producer import enqueue as enqueue_job
from app.modules.runtime.triggers._signing import verify_discord_ed25519
from app.platform.config import settings
from app.platform.context import current_workspace_id_or_none

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
    """Backwards-compat shim — delegates to the shared Ed25519 helper."""
    verify_discord_ed25519(
        raw_body=raw_body,
        public_key_hex=public_key_hex,
        signature_hex=signature_hex,
        timestamp_header=timestamp,
        window_seconds=_REPLAY_WINDOW_SECONDS,
        now=now,
    )


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
