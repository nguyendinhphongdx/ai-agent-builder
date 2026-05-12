"""Scheduled-trigger logic — cron parsing, workflow-save sync, due
claiming.

The CRUD interface for scheduled triggers is unified into the
generic trigger CRUD (``modules.runtime.triggers.service``); this
module retains the *internal* helpers that workflow-save logic and
the background scheduler tick both depend on:

  validate_cron / compute_next_run_at  — cron string → datetime
  sync_from_workflow                   — reconcile cron_trigger nodes
                                          ↔ ``triggers`` rows on save
  claim_due                            — fetch + advance due rows
                                          for the scheduler tick
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trigger import TRIGGER_TYPE_SCHEDULED, Trigger
from app.models.workflow import Workflow

logger = logging.getLogger("agentforge")

CRON_TRIGGER_NODE_TYPE = "cron_trigger"


class InvalidCronExpression(ValueError):
    """Raised when a cron expression doesn't parse."""


def _croniter():
    try:
        from croniter import croniter  # type: ignore[import-untyped]
    except ImportError as exc:
        raise InvalidCronExpression(
            "croniter not installed — cron triggers are unavailable"
        ) from exc
    return croniter


def _resolve_tz(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name or "UTC")
    except ZoneInfoNotFoundError:
        logger.warning("scheduled_triggers: unknown timezone %r → UTC", name)
        return ZoneInfo("UTC")


def validate_cron(expression: str) -> None:
    cron_cls = _croniter()
    if not cron_cls.is_valid(expression):
        raise InvalidCronExpression(f"Invalid cron expression: {expression!r}")


def compute_next_run_at(
    expression: str, tz_name: str, *, from_dt: datetime | None = None
) -> datetime:
    cron_cls = _croniter()
    tz = _resolve_tz(tz_name)
    base = (from_dt or datetime.now(timezone.utc)).astimezone(tz)
    try:
        ticker = cron_cls(expression, base)
    except Exception as exc:  # noqa: BLE001
        raise InvalidCronExpression(
            f"Invalid cron expression: {expression!r}"
        ) from exc
    next_local = ticker.get_next(datetime)
    if next_local.tzinfo is None:
        next_local = next_local.replace(tzinfo=tz)
    return next_local.astimezone(timezone.utc)


# ─── workflow-save sync ────────────────────────────────────────────


async def _get_by_workflow_node(
    db: AsyncSession, workflow_id: uuid.UUID, node_id: uuid.UUID
) -> Trigger | None:
    """Find the scheduled row that pairs with one cron_trigger node.
    Uses the partial unique index ``uq_triggers_scheduled_node`` on
    ``(workflow_id, config->>'node_id') WHERE type='scheduled'``."""
    return await db.scalar(
        select(Trigger).where(
            Trigger.type == TRIGGER_TYPE_SCHEDULED,
            Trigger.workflow_id == workflow_id,
            Trigger.config["node_id"].astext == str(node_id),
        )
    )


async def _upsert(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    workflow_id: uuid.UUID,
    node_id: uuid.UUID,
    cron_expression: str,
    timezone_name: str,
    payload: dict[str, Any],
    created_by: uuid.UUID | None,
    is_active: bool = True,
) -> Trigger:
    """Create or update the trigger row for ``(workflow_id, node_id)``."""
    validate_cron(cron_expression)
    next_run_at = compute_next_run_at(cron_expression, timezone_name)

    existing = await _get_by_workflow_node(db, workflow_id, node_id)
    if existing is not None:
        existing.config = {
            "node_id": str(node_id),
            "cron_expression": cron_expression,
            "timezone": timezone_name,
            "payload": payload,
        }
        existing.is_active = is_active
        existing.next_run_at = next_run_at
        await db.flush()
        return existing

    row = Trigger(
        type=TRIGGER_TYPE_SCHEDULED,
        workspace_id=workspace_id,
        workflow_id=workflow_id,
        name=cron_expression,
        config={
            "node_id": str(node_id),
            "cron_expression": cron_expression,
            "timezone": timezone_name,
            "payload": payload,
        },
        is_active=is_active,
        next_run_at=next_run_at,
        created_by=created_by,
    )
    db.add(row)
    await db.flush()
    return row


async def sync_from_workflow(
    db: AsyncSession, workflow: Workflow, *, created_by: uuid.UUID | None = None
) -> None:
    """Reconcile scheduled trigger rows with the workflow's current
    cron_trigger nodes. Called by ``save_workflow_graph`` after the
    graph has been rewritten.

      1. Collect every cron_trigger node + its config from the new graph.
      2. UPSERT one row per node — preserves last_fired_at on edits.
      3. DELETE rows whose node_id isn't in the new set.

    Bad cron expressions skip with a warning rather than aborting —
    the UI can flag them on the affected node.
    """
    target_nodes: dict[uuid.UUID, dict[str, Any]] = {
        n.id: (n.config or {})
        for n in workflow.nodes
        if n.node_type == CRON_TRIGGER_NODE_TYPE
    }

    existing_rows = (
        await db.scalars(
            select(Trigger).where(
                Trigger.type == TRIGGER_TYPE_SCHEDULED,
                Trigger.workflow_id == workflow.id,
            )
        )
    ).all()
    existing_by_node = {
        uuid.UUID(r.config["node_id"]): r for r in existing_rows if "node_id" in r.config
    }

    for node_id, config in target_nodes.items():
        cron = config.get("cron")
        if not cron:
            continue  # node config not filled in yet
        try:
            await _upsert(
                db,
                workspace_id=workflow.workspace_id,
                workflow_id=workflow.id,
                node_id=node_id,
                cron_expression=cron,
                timezone_name=config.get("timezone", "UTC"),
                payload=config.get("payload", {}),
                created_by=created_by,
                is_active=bool(config.get("enabled", True)),
            )
        except InvalidCronExpression as exc:
            logger.warning(
                "scheduled trigger sync: skipping node %s — %s", node_id, exc
            )

    for node_id, row in existing_by_node.items():
        if node_id not in target_nodes:
            await db.delete(row)
    await db.flush()


# ─── scheduler tick helper ─────────────────────────────────────────


async def claim_due(
    db: AsyncSession, *, now: datetime | None = None, limit: int = 50
) -> list[Trigger]:
    """Return scheduled trigger rows due to fire, advancing their
    ``next_run_at`` in the same transaction. Uses ``FOR UPDATE SKIP
    LOCKED`` so multiple scheduler replicas don't double-fire.
    """
    cron_cls = _croniter()
    now = now or datetime.now(timezone.utc)

    rows = (
        await db.execute(
            select(Trigger)
            .where(
                Trigger.type == TRIGGER_TYPE_SCHEDULED,
                Trigger.is_active.is_(True),
                Trigger.next_run_at <= now,
            )
            .order_by(Trigger.next_run_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
    ).scalars().all()

    for row in rows:
        cfg = row.config or {}
        try:
            tz = _resolve_tz(cfg.get("timezone", "UTC"))
            base = now.astimezone(tz)
            ticker = cron_cls(cfg["cron_expression"], base)
            next_local = ticker.get_next(datetime)
            if next_local.tzinfo is None:
                next_local = next_local.replace(tzinfo=tz)
            row.next_run_at = next_local.astimezone(timezone.utc)
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "scheduled trigger %s has bad cron — pausing. %s", row.id, exc
            )
            row.is_active = False

    await db.flush()
    return list(rows)
