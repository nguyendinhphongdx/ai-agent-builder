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

    handler = _resolve_handler(event_type)
    if handler is None:
        # Unknown / unhandled event — still 200 so Stripe stops
        # retrying it. We don't record it in the dedupe table because
        # there's no side effect to guard.
        return JSONResponse({"received": True, "ignored": True})

    obj = event.get("data", {}).get("object", {})
    async with async_session_factory() as db:
        try:
            claimed = await _claim_event(db, event_id, event_type)
            if not claimed:
                # Re-delivery of an already-processed event. The dedupe
                # row is committed, so a redundant SELECT would also
                # return it; we just short-circuit here.
                logger.info("stripe webhook: dedupe skip event=%s", event_id)
                await db.commit()
                return JSONResponse({"received": True, "deduped": True})
            await handler(db, obj)
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


def _resolve_handler(event_type: str):
    """Map event.type → coroutine ``handler(db, obj)``.

    Lazy import per branch so we don't pull every subsystem in just to
    receive the receiver module. Returns None for events we don't
    care about — caller acks with 200 + ``ignored=True`` so Stripe
    stops retrying.
    """
    if event_type == "checkout.session.completed":
        return handle_checkout_completed

    if event_type == "account.updated":
        from app.modules.commerce.payments.payouts.service import sync_account_from_event

        return sync_account_from_event

    if event_type in (
        "customer.subscription.created",
        "customer.subscription.updated",
    ):
        from app.modules.commerce.payments.subscriptions.webhooks import handle_subscription_event

        return handle_subscription_event

    if event_type == "customer.subscription.deleted":
        from app.modules.commerce.payments.subscriptions.webhooks import handle_subscription_deleted

        return handle_subscription_deleted

    if event_type in ("invoice.paid", "invoice.payment_succeeded"):
        from app.modules.commerce.payments.subscriptions.webhooks import handle_invoice_paid

        return handle_invoice_paid

    if event_type == "invoice.payment_failed":
        from app.modules.commerce.payments.subscriptions.webhooks import (
            handle_invoice_payment_failed,
        )

        return handle_invoice_payment_failed

    return None
