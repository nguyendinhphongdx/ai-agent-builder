"""Stripe webhook endpoint for the Hub.

Mounted at ``/api/webhooks/stripe`` (separate from ``/api/webhooks/{wf}/...``
which handles workflow triggers — different concern, different signature
scheme).

Source-of-truth event: ``checkout.session.completed`` — fires once per
successful checkout. We mark the Purchase paid + fork the agent.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.db.session import async_session_factory
from app.hub.payment import handle_checkout_completed, is_stripe_configured

logger = logging.getLogger("agentforge")

router = APIRouter(prefix="/webhooks/stripe", tags=["stripe"])


@router.post("")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="stripe-signature"),
):
    """Stripe webhook receiver. Verifies signature → routes to handler.

    Stripe retries on non-2xx, so we return 200 even when an event is
    irrelevant (no-op) to avoid repeated deliveries clogging the log.
    """
    if not is_stripe_configured():
        # Treat as 404 — endpoint genuinely doesn't exist in this deploy.
        raise HTTPException(status_code=404, detail="Stripe webhook not configured")

    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe signature")

    payload = await request.body()

    import stripe

    try:
        # construct_event verifies the HMAC signature using the webhook
        # secret. Throws SignatureVerificationError on bad signature.
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
        # Use a dedicated session because the request DB scope ends fast and
        # we want this commit to be atomic with the fork it produces.
        async with async_session_factory() as db:
            try:
                await handle_checkout_completed(db, session)
                await db.commit()
            except Exception:
                logger.exception("stripe webhook: handler failed")
                await db.rollback()
                # Return 500 so Stripe retries.
                raise HTTPException(status_code=500, detail="Handler failed")

    elif event_type == "account.updated":
        # Stripe Connect — author finished/changed onboarding state. Mirror
        # ``charges_enabled`` / ``payouts_enabled`` onto the User row so the
        # publish-paid gate doesn't have to round-trip Stripe.
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

    # All other event types are explicitly accepted-and-ignored — Stripe
    # sends a lot of events we don't care about (charge.updated, etc.)
    return JSONResponse({"received": True})
