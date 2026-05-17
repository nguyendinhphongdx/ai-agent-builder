"""Stripe webhook receiver.

Verifies signature → dedupes by event.id → routes events:
- ``checkout.session.completed`` → mark Purchase paid + fork agent.
- ``account.updated`` → mirror Connect onboarding flags onto User row
  (handler lives in ``app.modules.commerce.payments.payouts.service`` since it's an author-side
  concern, not a buyer-side checkout one).
- ``customer.subscription.{created,updated,deleted}`` → sync OrgSub.
- ``invoice.paid`` / ``invoice.payment_succeeded`` → clear past_due,
   roll period window.
- ``invoice.payment_failed`` → flip status → past_due.

Idempotency: every event id is recorded in ``stripe_webhook_events``
via INSERT … ON CONFLICT DO NOTHING. Re-deliveries (Stripe retries on
non-2xx, occasionally even on 2xx) short-circuit with a 200 before
the handler runs again. The insert sits inside the handler's
transaction so a successful processing commits the dedupe row + the
side effects together; a failing handler rolls both back and the
next retry reprocesses cleanly.

Stripe retries on non-2xx, so we return 200 even when an event is
irrelevant (no-op) to avoid repeated deliveries clogging the log.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.stripe_webhook_event import StripeWebhookEvent
from app.modules.commerce.payments.checkout.providers.stripe import (
    handle_checkout_completed,
    is_stripe_configured,
)
from app.platform.config import settings
from app.platform.db.session import async_session_factory

logger = logging.getLogger("agentforge")

router = APIRouter(prefix="/webhooks/stripe", tags=["webhooks"])


async def _claim_event(db, event_id: str, event_type: str) -> bool:
    """Reserve this event id for processing inside the current txn.

    Returns True when the insert took (first time we've seen this
    event), False when the row already existed (re-delivery — caller
    should short-circuit to 200 without re-running side effects).

    The insert participates in the handler's transaction: rollback on
    handler failure clears the row, so the next Stripe retry sees
    the event as un-processed and runs the handler again. This is
    why we don't commit the dedupe row separately.
    """
    stmt = (
        pg_insert(StripeWebhookEvent)
        .values(event_id=event_id, event_type=event_type)
        .on_conflict_do_nothing(index_elements=["event_id"])
    )
    result = await db.execute(stmt)
    return result.rowcount > 0


@router.post("")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="stripe-signature"),
):
    if not is_stripe_configured():
        raise HTTPException(status_code=404, detail="Stripe webhook not configured")
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe signature")

    payload = await request.body()

    import stripe

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_id = event.get("id") or ""
    event_type = event.get("type") or ""
    logger.info(f"stripe webhook: type={event_type} id={event_id}")

    # Dispatch decision before opening the DB transaction so we don't
    # claim a dedupe row for events we'd just ignore.
    dispatch = _resolve_dispatch(event_type)
    if dispatch is None:
        return JSONResponse({"received": True, "ignored": True})

    async with async_session_factory() as db:
        try:
            claimed = await _claim_event(db, event_id, event_type)
            if not claimed:
                logger.info("stripe webhook: dedupe skip event=%s", event_id)
                await db.commit()
                return JSONResponse({"received": True, "deduped": True})
            await dispatch(db, event)
            await db.commit()
        except Exception:
            logger.exception(
                "stripe webhook: handler failed for type=%s id=%s",
                event_type,
                event_id,
            )
            await db.rollback()
            raise HTTPException(status_code=500, detail="Handler failed")

    return JSONResponse({"received": True})


# ─── Per-concern adapters ────────────────────────────────────────
# Each adapter wraps the right downstream handler in the uniform
# ``async (db, event) -> None`` shape used by the dispatcher table.


async def _dispatch_hub_checkout(db, event: dict) -> None:
    obj = event.get("data", {}).get("object", {})
    await handle_checkout_completed(db, obj)


async def _dispatch_connect_account_update(db, event: dict) -> None:
    from app.modules.commerce.payments.payouts.service import sync_account_from_event

    obj = event.get("data", {}).get("object", {})
    await sync_account_from_event(db, obj)


async def _dispatch_subscription(db, event: dict) -> None:
    from app.modules.commerce.payments.subscriptions.providers.stripe import (
        StripeSubscriptionProvider,
    )

    await StripeSubscriptionProvider().process_event(db, event=event)


def _resolve_dispatch(event_type: str):
    """Map event type → uniform adapter, or None to ignore.

    Three flows share this single Stripe URL (Stripe Dashboard only
    lets you configure one webhook endpoint per signing secret):
      * Hub one-time checkout (checkout.session.completed)
      * Connect onboarding flag sync (account.updated)
      * Org subscriptions (customer.subscription.* + invoice.*),
        delegated to StripeSubscriptionProvider.process_event.
    """
    if event_type == "checkout.session.completed":
        return _dispatch_hub_checkout
    if event_type == "account.updated":
        return _dispatch_connect_account_update

    # Subscription provider self-declares which event types it owns.
    # Lazy import so deployments without Stripe don't pay for the
    # provider class load at module import time.
    from app.modules.commerce.payments.subscriptions.providers.stripe import (
        StripeSubscriptionProvider,
    )

    if StripeSubscriptionProvider.handles_event(event_type):
        return _dispatch_subscription
    return None
