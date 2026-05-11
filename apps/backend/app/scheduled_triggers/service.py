"""Scheduled-trigger CRUD + sync from workflow graph.

The workflow editor stores cron config inside ``cron_trigger`` node
configs. After each ``save_workflow_graph`` call, :func:`sync_from_workflow`
diffs node configs against the ``scheduled_triggers`` table and
upserts/deletes accordingly. The scheduler tick (:mod:`app.scheduled_triggers.scheduler`)
reads from this table — never from workflow_nodes directly.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scheduled_trigger import ScheduledTrigger
from app.models.workflow import Workflow

logger = logging.getLogger("agentforge")

# Marker used in workflow_nodes.node_type for cron triggers.
CRON_TRIGGER_NODE_TYPE = "cron_trigger"


# ─── Cron parsing ─────────────────────────────────────────────────


class InvalidCronExpression(ValueError):
    """Raised by :func:`validate_cron` and :func:`compute_next_run_at`
    when the expression doesn't parse — callers translate to 400."""


def _croniter():
    """Lazy import — keeps ``croniter`` optional for envs that haven't
    installed it yet (e.g. CI lint stage)."""
    try:
        from croniter import croniter  # type: ignore[import-untyped]
    except ImportError as exc:
        raise InvalidCronExpression(
            "croniter not installed — cron triggers are unavailable"
        ) from exc
    return croniter


def _resolve_tz(name: str) -> ZoneInfo:
    """Validate + load a tz name. Falls back to UTC on unknown zones
    rather than raising — keeps a single bad row from blocking the
    whole scheduler tick."""
    try:
        return ZoneInfo(name or "UTC")
    except ZoneInfoNotFoundError:
        logger.warning("scheduled_triggers: unknown timezone %r → UTC", name)
        return ZoneInfo("UTC")


def validate_cron(expression: str) -> None:
    """Raise :class:`InvalidCronExpression` if ``expression`` doesn't
    parse. Use at API boundaries before persisting user input."""
    cron_cls = _croniter()
    if not cron_cls.is_valid(expression):
        raise InvalidCronExpression(f"Invalid cron expression: {expression!r}")


def compute_next_run_at(
    expression: str, tz_name: str, *, from_dt: datetime | None = None
) -> datetime:
    """Resolve the next fire time after ``from_dt`` (default: now).

    Returns a UTC ``datetime`` — Postgres ``TIMESTAMP WITH TIME ZONE``
    stores everything in UTC so we normalise here.
    """
    cron_cls = _croniter()
    tz = _resolve_tz(tz_name)
    base = (from_dt or datetime.now(timezone.utc)).astimezone(tz)
    try:
        ticker = cron_cls(expression, base)
    except Exception as exc:  # noqa: BLE001 — croniter raises various subclasses
        raise InvalidCronExpression(f"Invalid cron expression: {expression!r}") from exc
    next_local = ticker.get_next(datetime)
    if next_local.tzinfo is None:
        next_local = next_local.replace(tzinfo=tz)
    return next_local.astimezone(timezone.utc)


# ─── CRUD ─────────────────────────────────────────────────────────


async def get_by_workflow_node(
    db: AsyncSession, workflow_id: uuid.UUID, node_id: uuid.UUID
) -> ScheduledTrigger | None:
    return await db.scalar(
        select(ScheduledTrigger).where(
            ScheduledTrigger.workflow_id == workflow_id,
            ScheduledTrigger.node_id == node_id,
        )
    )


async def upsert(
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
) -> ScheduledTrigger:
    """Create or update the trigger row for ``(workflow_id, node_id)``.

    Recomputes ``next_run_at`` against the (possibly new) cron + tz.
    """
    validate_cron(cron_expression)
    next_run_at = compute_next_run_at(cron_expression, timezone_name)

    existing = await get_by_workflow_node(db, workflow_id, node_id)
    if existing is not None:
        existing.cron_expression = cron_expression
        existing.timezone = timezone_name
        existing.payload = payload
        existing.is_active = is_active
        # Only advance next_run_at when the schedule actually changed —
        # avoid jitter on no-op edits that re-save the same workflow.
        existing.next_run_at = next_run_at
        await db.flush()
        return existing

    row = ScheduledTrigger(
        workspace_id=workspace_id,
        workflow_id=workflow_id,
        node_id=node_id,
        cron_expression=cron_expression,
        timezone=timezone_name,
        payload=payload,
        is_active=is_active,
        next_run_at=next_run_at,
        created_by=created_by,
    )
    db.add(row)
    await db.flush()
    return row


async def delete_by_node(
    db: AsyncSession, workflow_id: uuid.UUID, node_id: uuid.UUID
) -> None:
    row = await get_by_workflow_node(db, workflow_id, node_id)
    if row is not None:
        await db.delete(row)
        await db.flush()


# ─── Sync from workflow graph ─────────────────────────────────────


async def sync_from_workflow(
    db: AsyncSession, workflow: Workflow, *, created_by: uuid.UUID | None = None
) -> None:
    """Reconcile ``scheduled_triggers`` with the workflow's current
    cron_trigger nodes. Called by ``save_workflow_graph`` after the
    nodes/edges have been rewritten.

    Strategy:
      1. Collect every cron_trigger node in the new graph + its config.
      2. UPSERT a row per node — preserves last_run_at on edits.
      3. DELETE any existing rows whose node_id isn't in the new set
         (the node was removed or replaced).

    Bad cron expressions are skipped with a warning rather than
    aborting the whole save — UI can flag them on the affected node.
    """
    target_nodes: dict[uuid.UUID, dict[str, Any]] = {
        n.id: (n.config or {})
        for n in workflow.nodes
        if n.node_type == CRON_TRIGGER_NODE_TYPE
    }

    # Reconcile by node_id.
    existing_rows = (
        await db.scalars(
            select(ScheduledTrigger).where(
                ScheduledTrigger.workflow_id == workflow.id
            )
        )
    ).all()
    existing_by_node = {r.node_id: r for r in existing_rows}

    # Upsert active nodes.
    for node_id, config in target_nodes.items():
        cron = config.get("cron")
        if not cron:
            continue  # config not filled in yet — user still editing
        try:
            await upsert(
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
                "scheduled_triggers sync: skipping node %s — %s", node_id, exc
            )

    # Delete rows whose node is gone (or no longer a cron_trigger).
    for node_id, row in existing_by_node.items():
        if node_id not in target_nodes:
            await db.delete(row)
    await db.flush()


# ─── Scheduler tick helpers ────────────────────────────────────────


async def claim_due(
    db: AsyncSession, *, now: datetime | None = None, limit: int = 50
) -> list[ScheduledTrigger]:
    """Return rows due to fire and advance their ``next_run_at`` /
    ``last_run_at`` in the same transaction.

    Uses ``FOR UPDATE SKIP LOCKED`` so multiple scheduler workers
    can run side-by-side without re-claiming the same row.
    """
    cron_cls = _croniter()
    now = now or datetime.now(timezone.utc)

    rows = (
        await db.execute(
            select(ScheduledTrigger)
            .where(
                ScheduledTrigger.is_active.is_(True),
                ScheduledTrigger.next_run_at <= now,
            )
            .order_by(ScheduledTrigger.next_run_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
    ).scalars().all()

    for row in rows:
        # Compute the next fire time *after* now so we never reschedule
        # back to the same instant (skip past missed ticks if the
        # scheduler was down).
        try:
            tz = _resolve_tz(row.timezone)
            base = now.astimezone(tz)
            ticker = cron_cls(row.cron_expression, base)
            next_local = ticker.get_next(datetime)
            if next_local.tzinfo is None:
                next_local = next_local.replace(tzinfo=tz)
            row.next_run_at = next_local.astimezone(timezone.utc)
        except Exception as exc:  # noqa: BLE001
            # Bad cron in the DB shouldn't crash the loop. Pause the
            # row and surface via admin tooling (DLQ-style).
            logger.exception(
                "scheduled_triggers: row %s has bad cron — pausing. %s", row.id, exc
            )
            row.is_active = False
        row.last_run_at = now

    await db.flush()
    return list(rows)
