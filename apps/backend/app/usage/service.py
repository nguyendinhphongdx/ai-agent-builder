"""Usage-event writer + aggregator.

The writer is fire-and-forget by convention — never raises out to
the caller. If we drop an event row because the DB blipped, that's
preferable to refusing a successful LLM response.

Cost is estimated at write time using the static pricing table.
For replays after a rate change we'd recompute, but day-to-day the
stored cost_usd is correct.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.context import current_user_id_or_none, current_workspace_id_or_none
from app.models.usage_event import (
    EVENT_EMBED_BATCH,
    EVENT_KB_QUERY,
    EVENT_LLM_CALL,
    EVENT_TOOL_CALL,
    UsageEvent,
)
from app.usage.pricing import estimate_cost_usd

logger = logging.getLogger("agentforge")


def _split_model_id(model_id: str | None) -> tuple[str | None, str | None]:
    """Agents store model as ``"openai/gpt-4o"``. Split into provider
    + model so the pricing table can resolve it. Bare strings (no
    slash) are treated as model-only; provider stays None.
    """
    if not model_id:
        return None, None
    if "/" in model_id:
        provider, model = model_id.split("/", 1)
        return provider.strip() or None, model.strip() or None
    return None, model_id.strip() or None


async def log_llm_call(
    db: AsyncSession,
    *,
    model_id: str | None,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    latency_ms: int | None,
    agent_id: uuid.UUID | None = None,
    conversation_id: uuid.UUID | None = None,
    workflow_run_id: uuid.UUID | None = None,
    workspace_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> UsageEvent | None:
    """Record one LLM call. Auto-fills tenant context from the request
    ContextVars when args omitted.

    Returns the row on success, ``None`` when the write failed (we
    swallow the exception so the surrounding business path proceeds).
    """
    workspace_id = workspace_id or current_workspace_id_or_none()
    if workspace_id is None:
        # System-level events (cron tick LLM call, ingestion embed)
        # without a tenant scope — log a warning and skip. Better than
        # writing orphan rows that don't aggregate cleanly.
        logger.debug("usage.log_llm_call: no workspace context, skipping")
        return None
    user_id = user_id if user_id is not None else current_user_id_or_none()

    provider, model = _split_model_id(model_id)
    total = (prompt_tokens or 0) + (completion_tokens or 0) if (prompt_tokens or completion_tokens) else None
    cost = estimate_cost_usd(
        provider=provider,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )

    row = UsageEvent(
        workspace_id=workspace_id,
        user_id=user_id,
        agent_id=agent_id,
        conversation_id=conversation_id,
        workflow_run_id=workflow_run_id,
        event_type=EVENT_LLM_CALL,
        provider=provider,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total,
        cost_usd=cost,
        latency_ms=latency_ms,
        data=metadata or {},
    )
    try:
        db.add(row)
        await db.flush()
    except Exception:
        # Never break the request because we couldn't write telemetry.
        logger.exception("usage.log_llm_call: write failed")
        return None
    return row


async def log_tool_call(
    db: AsyncSession,
    *,
    tool_name: str,
    latency_ms: int | None,
    agent_id: uuid.UUID | None = None,
    conversation_id: uuid.UUID | None = None,
    workspace_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    success: bool = True,
    metadata: dict[str, Any] | None = None,
) -> UsageEvent | None:
    """Record one tool execution — no tokens / cost, just latency
    + the tool name + success flag in metadata."""
    workspace_id = workspace_id or current_workspace_id_or_none()
    if workspace_id is None:
        return None
    user_id = user_id if user_id is not None else current_user_id_or_none()

    meta = {"tool": tool_name, "success": success}
    if metadata:
        meta.update(metadata)
    row = UsageEvent(
        workspace_id=workspace_id,
        user_id=user_id,
        agent_id=agent_id,
        conversation_id=conversation_id,
        event_type=EVENT_TOOL_CALL,
        latency_ms=latency_ms,
        data=meta,
    )
    try:
        db.add(row)
        await db.flush()
    except Exception:
        logger.exception("usage.log_tool_call: write failed")
        return None
    return row


# ─── Aggregations for the cost dashboard ──────────────────────────


async def workspace_totals(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    *,
    since: datetime | None = None,
    until: datetime | None = None,
) -> dict[str, Any]:
    """Single-shot rollup — counts + totals scoped to one workspace.
    Returns 0s for missing data so the FE never has to handle None.
    """
    if since is None:
        since = datetime.now(timezone.utc) - timedelta(days=30)

    stmt = select(
        func.count(UsageEvent.id).label("count"),
        func.coalesce(func.sum(UsageEvent.total_tokens), 0).label("tokens"),
        func.coalesce(func.sum(UsageEvent.cost_usd), Decimal("0")).label("cost"),
        func.coalesce(func.avg(UsageEvent.latency_ms), 0).label("avg_latency_ms"),
    ).where(
        UsageEvent.workspace_id == workspace_id,
        UsageEvent.created_at >= since,
    )
    if until is not None:
        stmt = stmt.where(UsageEvent.created_at < until)
    row = (await db.execute(stmt)).first()
    return {
        "count": int(row.count or 0),
        "tokens": int(row.tokens or 0),
        "cost_usd": float(row.cost or 0),
        "avg_latency_ms": float(row.avg_latency_ms or 0),
        "since": since.isoformat(),
        "until": (until or datetime.now(timezone.utc)).isoformat(),
    }


async def workspace_daily(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    *,
    since: datetime | None = None,
    until: datetime | None = None,
) -> list[dict[str, Any]]:
    """Daily-bucketed rollup for the cost chart. Returns one row per
    UTC day in range, even if it has zero events — the FE renders a
    contiguous timeline."""
    if since is None:
        since = datetime.now(timezone.utc) - timedelta(days=30)
    if until is None:
        until = datetime.now(timezone.utc)

    bucket = func.date_trunc("day", UsageEvent.created_at).label("day")
    stmt = (
        select(
            bucket,
            func.count(UsageEvent.id).label("count"),
            func.coalesce(func.sum(UsageEvent.total_tokens), 0).label("tokens"),
            func.coalesce(func.sum(UsageEvent.cost_usd), Decimal("0")).label("cost"),
        )
        .where(
            UsageEvent.workspace_id == workspace_id,
            UsageEvent.created_at >= since,
            UsageEvent.created_at < until,
        )
        .group_by(bucket)
        .order_by(bucket)
    )
    rows = (await db.execute(stmt)).all()
    return [
        {
            "day": r.day.date().isoformat(),
            "count": int(r.count or 0),
            "tokens": int(r.tokens or 0),
            "cost_usd": float(r.cost or 0),
        }
        for r in rows
    ]


async def workspace_by_model(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    *,
    since: datetime | None = None,
) -> list[dict[str, Any]]:
    """Per-(provider, model) breakdown for the "where is the spend
    going" table on the dashboard."""
    if since is None:
        since = datetime.now(timezone.utc) - timedelta(days=30)
    stmt = (
        select(
            UsageEvent.provider,
            UsageEvent.model,
            func.count(UsageEvent.id).label("count"),
            func.coalesce(func.sum(UsageEvent.total_tokens), 0).label("tokens"),
            func.coalesce(func.sum(UsageEvent.cost_usd), Decimal("0")).label("cost"),
        )
        .where(
            UsageEvent.workspace_id == workspace_id,
            UsageEvent.event_type == EVENT_LLM_CALL,
            UsageEvent.created_at >= since,
        )
        .group_by(UsageEvent.provider, UsageEvent.model)
        .order_by(func.sum(UsageEvent.cost_usd).desc().nullslast())
    )
    rows = (await db.execute(stmt)).all()
    return [
        {
            "provider": r.provider,
            "model": r.model,
            "count": int(r.count or 0),
            "tokens": int(r.tokens or 0),
            "cost_usd": float(r.cost or 0),
        }
        for r in rows
    ]


__all__ = [
    "log_llm_call",
    "log_tool_call",
    "workspace_totals",
    "workspace_daily",
    "workspace_by_model",
    "EVENT_LLM_CALL",
    "EVENT_KB_QUERY",
    "EVENT_TOOL_CALL",
    "EVENT_EMBED_BATCH",
]
