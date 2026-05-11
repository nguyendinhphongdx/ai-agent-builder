"""Slack trigger CRUD + event dispatcher.

The event receiver (router) decodes the Slack envelope, then calls
``dispatch_event`` which finds matching triggers and enqueues a
workflow run per match.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.context import current_workspace_id_or_none
from app.jobs import types as job_types
from app.jobs.producer import enqueue as enqueue_job
from app.models.slack_trigger import (
    SLACK_EVENT_APP_MENTION,
    SLACK_EVENT_MESSAGE,
    SLACK_EVENT_SLASH_COMMAND,
    SlackTrigger,
)
from app.models.workflow import Workflow
from app.slack_triggers.schemas import SlackTriggerCreate, SlackTriggerUpdate

logger = logging.getLogger("agentforge")


# ─── CRUD ──────────────────────────────────────────────────────────


async def list_triggers(
    db: AsyncSession, workflow_id: uuid.UUID | None = None
) -> Sequence[SlackTrigger]:
    workspace_id = current_workspace_id_or_none()
    stmt = select(SlackTrigger).order_by(SlackTrigger.created_at.desc())
    if workspace_id is not None:
        stmt = stmt.where(SlackTrigger.workspace_id == workspace_id)
    if workflow_id is not None:
        stmt = stmt.where(SlackTrigger.workflow_id == workflow_id)
    return (await db.execute(stmt)).scalars().all()


async def get_trigger(
    db: AsyncSession, trigger_id: uuid.UUID
) -> SlackTrigger | None:
    workspace_id = current_workspace_id_or_none()
    stmt = select(SlackTrigger).where(SlackTrigger.id == trigger_id)
    if workspace_id is not None:
        stmt = stmt.where(SlackTrigger.workspace_id == workspace_id)
    return await db.scalar(stmt)


async def create_trigger(
    db: AsyncSession, payload: SlackTriggerCreate
) -> SlackTrigger:
    workspace_id = current_workspace_id_or_none()
    if workspace_id is None:
        raise ValueError("no_active_workspace")
    wf = await db.scalar(
        select(Workflow).where(
            Workflow.id == payload.workflow_id,
            Workflow.workspace_id == workspace_id,
        )
    )
    if wf is None:
        raise ValueError("workflow_not_found")

    row = SlackTrigger(
        workflow_id=payload.workflow_id,
        workspace_id=workspace_id,
        name=payload.name,
        slack_team_id=payload.slack_team_id,
        filter_event_type=payload.filter_event_type,
        filter_channel_id=payload.filter_channel_id,
        filter_command=payload.filter_command,
        filter_keyword=payload.filter_keyword,
        is_active=payload.is_active,
    )
    db.add(row)
    await db.flush()
    return row


async def update_trigger(
    db: AsyncSession, trigger: SlackTrigger, payload: SlackTriggerUpdate
) -> SlackTrigger:
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(trigger, k, v)
    await db.flush()
    return trigger


async def delete_trigger(db: AsyncSession, trigger: SlackTrigger) -> None:
    await db.delete(trigger)
    await db.flush()


# ─── Event dispatch ────────────────────────────────────────────────


def _matches(trigger: SlackTrigger, event: dict[str, Any], event_type: str) -> bool:
    """Return True iff this trigger should fire for ``event``."""
    if trigger.filter_event_type != event_type:
        return False
    if trigger.filter_channel_id and event.get("channel") != trigger.filter_channel_id:
        return False
    if trigger.filter_command:
        # Slash command shape: payload is form-encoded with
        # 'command' field. The slash is included.
        if event.get("command") != trigger.filter_command:
            return False
    if trigger.filter_keyword:
        text = event.get("text") or ""
        if trigger.filter_keyword.lower() not in text.lower():
            return False
    return True


async def dispatch_event(
    db: AsyncSession,
    *,
    team_id: str,
    event_type: str,
    event: dict[str, Any],
) -> int:
    """Find every matching active trigger for (team_id, event_type)
    and enqueue a workflow run per match. Returns the dispatch count.

    Index ``ix_slack_triggers_team_event`` covers this lookup so we
    don't scan the whole table on busy Slack workspaces.
    """
    rows = (
        await db.execute(
            select(SlackTrigger).where(
                SlackTrigger.slack_team_id == team_id,
                SlackTrigger.filter_event_type == event_type,
                SlackTrigger.is_active.is_(True),
            )
        )
    ).scalars().all()

    dispatched = 0
    for trigger in rows:
        if not _matches(trigger, event, event_type):
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
                    "trigger": "slack",
                    "trigger_id": str(trigger.id),
                    "slack": {
                        "team_id": team_id,
                        "event_type": event_type,
                        "event": event,
                    },
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


__all__ = [
    "list_triggers",
    "get_trigger",
    "create_trigger",
    "update_trigger",
    "delete_trigger",
    "dispatch_event",
    "SLACK_EVENT_APP_MENTION",
    "SLACK_EVENT_MESSAGE",
    "SLACK_EVENT_SLASH_COMMAND",
]
