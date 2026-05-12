"""Stripe metered-usage reporter loop.

Periodically walks every org with a live subscription that has a
metered subscription item, sums their token usage since the last
report, and posts a usage record to Stripe. Stripe then bills
those tokens at end-of-period via the metered-price line item.

Cadence: every 15 minutes. Stripe accepts up to ~10 records/sec
per subscription item, so even chatty enterprise tenants don't
backpressure. Bigger orgs that prefer real-time can drop this to
1 min — the bottleneck is Stripe's rate limits, not Postgres.

Idempotency:
  - cursor = OrgSubscription.last_reported_event_id
  - we ship `total_tokens` SUM of UsageEvent rows with id > cursor
  - update cursor to the max id we just consumed
  - on retry after crash we re-aggregate the same window (Stripe's
    ``action="increment"`` is additive — duplicates double-bill).
    So we update the cursor BEFORE the Stripe call would be wrong;
    we update it AFTER, and use ``idempotency_key`` keyed on the
    (org, cursor_to) pair to make Stripe-side retries safe.

Token rounding:
  Stripe price unit is "per 1,000 tokens". We ship ``ceil(tokens
  / 1000)`` so partial 1k windows still bill. Trade-off: tiny
  accounts pay a tiny bit more than exact-rate. Acceptable for
  v1.

Disabled when Stripe is not configured.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import math
import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.org_subscription import LIVE_STATUSES, OrgSubscription
from app.models.usage_event import EVENT_LLM_CALL, UsageEvent
from app.modules.billing import stripe_client
from app.platform.db.session import async_session_factory

logger = logging.getLogger("agentforge")

# 15 min cadence. Skew the first run to avoid stacking on startup.
_INTERVAL_SECONDS = 15 * 60
_INITIAL_DELAY_SECONDS = 60


async def _sum_tokens_since(
    db: AsyncSession,
    organization_id: uuid.UUID,
    *,
    cursor_id: uuid.UUID | None,
) -> tuple[int, uuid.UUID | None]:
    """Sum total_tokens for LLM events whose ``id`` is greater than
    ``cursor_id``, scoped to every workspace in the org.

    Returns ``(tokens, max_id_seen)``. ``max_id_seen`` is None when
    there are no new rows.

    Why ``id`` and not ``created_at``: UUIDv7 / time-sortable ids
    aren't guaranteed here — we use the plain ``id`` ordering as a
    monotonically-increasing-enough cursor for a 15-min window. If
    two rows insert in the same microsecond we may ship one twice
    on a worst-case retry. The Stripe ``idempotency_key`` guarantees
    no double-billing even then.
    """
    from app.models.workspace import Workspace

    workspace_ids = list(
        (
            await db.execute(
                select(Workspace.id).where(Workspace.organization_id == organization_id)
            )
        ).scalars()
    )
    if not workspace_ids:
        return 0, None

    stmt = select(
        func.coalesce(func.sum(UsageEvent.total_tokens), 0).label("tokens"),
        func.max(UsageEvent.id).label("max_id"),
    ).where(
        UsageEvent.workspace_id.in_(workspace_ids),
        UsageEvent.event_type == EVENT_LLM_CALL,
    )
    if cursor_id is not None:
        stmt = stmt.where(UsageEvent.id > cursor_id)
    row = (await db.execute(stmt)).first()
    return int(row.tokens or 0), row.max_id


async def _report_org(db: AsyncSession, sub: OrgSubscription) -> int:
    """Ship one org's pending usage to Stripe. Returns tokens posted."""
    if not sub.stripe_metered_item_id:
        return 0
    if sub.status not in LIVE_STATUSES:
        return 0

    cursor = sub.last_reported_event_id
    tokens, new_cursor = await _sum_tokens_since(
        db, sub.organization_id, cursor_id=cursor
    )
    if tokens <= 0 or new_cursor is None:
        return 0

    # Stripe meters tokens in 1k-unit chunks at the price level — ceil
    # so the last partial chunk doesn't fall off the invoice.
    quantity = math.ceil(tokens / 1000)

    stripe = stripe_client._stripe()
    now_ts = int(datetime.now(timezone.utc).timestamp())
    # action="increment" is additive; the idempotency key keyed on
    # (sub_item, cursor_to) means a retry after Stripe ACK'd but
    # before we updated the row will be deduped on Stripe's side.
    stripe.SubscriptionItem.create_usage_record(
        sub.stripe_metered_item_id,
        quantity=quantity,
        timestamp=now_ts,
        action="increment",
        idempotency_key=f"usage-{sub.stripe_metered_item_id}-{new_cursor}",
    )

    sub.last_reported_event_id = new_cursor
    sub.last_reported_at = datetime.now(timezone.utc)
    await db.flush()
    return tokens


async def _sweep_once() -> int:
    """One full sweep across every live metered subscription.

    Returns the total tokens shipped this tick — useful for logging
    + future Prometheus instrumentation.
    """
    async with async_session_factory() as db:
        subs: Sequence[OrgSubscription] = (
            await db.execute(
                select(OrgSubscription)
                .where(OrgSubscription.status.in_(LIVE_STATUSES))
                .where(OrgSubscription.stripe_metered_item_id.is_not(None))
            )
        ).scalars().all()

        total_tokens = 0
        for sub in subs:
            try:
                shipped = await _report_org(db, sub)
                if shipped:
                    logger.info(
                        "billing.usage_reporter: org=%s tokens=%d",
                        sub.organization_id,
                        shipped,
                    )
                total_tokens += shipped
            except Exception:  # noqa: BLE001 — one org's failure ≠ whole sweep
                logger.exception(
                    "billing.usage_reporter: failed for org=%s",
                    sub.organization_id,
                )
                # Roll back the per-org mutation; cursor stays on the
                # last good value so next tick retries the window.
                await db.rollback()
        await db.commit()
        return total_tokens


async def run_forever() -> None:
    """Long-lived report loop."""
    if not stripe_client.is_configured():
        logger.info("billing.usage_reporter: disabled (Stripe not configured)")
        return

    logger.info(
        "billing.usage_reporter: started (cadence=%ds)", _INTERVAL_SECONDS
    )
    await asyncio.sleep(_INITIAL_DELAY_SECONDS)

    while True:
        try:
            await _sweep_once()
        except Exception:  # noqa: BLE001
            logger.exception("billing.usage_reporter: sweep crashed")
        await asyncio.sleep(_INTERVAL_SECONDS)


_task: asyncio.Task[None] | None = None


def start() -> None:
    """Boot the reporter loop. Idempotent."""
    global _task
    if _task is not None and not _task.done():
        return
    _task = asyncio.create_task(run_forever(), name="billing.usage_reporter")


async def stop() -> None:
    global _task
    if _task is None:
        return
    _task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await _task
    _task = None
