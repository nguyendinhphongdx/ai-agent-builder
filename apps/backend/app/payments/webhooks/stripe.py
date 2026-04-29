"""Stripe webhook receiver.

Verifies signature → routes events:
- ``checkout.session.completed`` → mark Purchase paid + fork agent.
- ``account.updated`` → mirror Connect onboarding flags onto User row
  (handler lives in ``app.payouts.service`` since it's an author-side
  concern, not a buyer-side checkout one).

Stripe retries on non-2xx, so we return 200 even when an event is
irrelevant (no-op) to avoid repeated deliveries clogging the log.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.db.session import async_session_factory
from app.payments.providers.stripe import handle_checkout_completed, is_stripe_configured

logger = logging.getLogger("agentforge")

router = APIRouter(prefix="/webhooks/stripe", tags=["webhooks"])


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

    event_type = event.get("type")
    logger.info(f"stripe webhook: type={event_type} id={event.get('id')}")

    if event_type == "checkout.session.completed":
        session = event.get("data", {}).get("object", {})
        async with async_session_factory() as db:
            try:
                await handle_checkout_completed(db, session)
                await db.commit()
            except Exception:
                logger.exception("stripe webhook: handler failed")
                await db.rollback()
                raise HTTPException(status_code=500, detail="Handler failed")

    elif event_type == "account.updated":
        from app.payouts.service import sync_account_from_event

        account = event.get("data", {}).get("object", {})
        async with async_session_factory() as db:
            try:
                await sync_account_from_event(db, account)
                await db.commit()
            except Exception:
                logger.exception("stripe webhook: connect sync failed")
                await db.rollback()
                raise HTTPException(status_code=500, detail="Handler failed")

    return JSONResponse({"received": True})
