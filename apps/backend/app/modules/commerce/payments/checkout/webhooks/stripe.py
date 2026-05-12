"""Stripe webhook receiver.

Verifies signature → routes events:
- ``checkout.session.completed`` → mark Purchase paid + fork agent.
- ``account.updated`` → mirror Connect onboarding flags onto User row
  (handler lives in ``app.modules.commerce.payments.payouts.service`` since it's an author-side
  concern, not a buyer-side checkout one).

Stripe retries on non-2xx, so we return 200 even when an event is
irrelevant (no-op) to avoid repeated deliveries clogging the log.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from app.modules.commerce.payments.checkout.providers.stripe import (
    handle_checkout_completed,
    is_stripe_configured,
)
from app.platform.config import settings
from app.platform.db.session import async_session_factory

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
        from app.modules.commerce.payments.payouts.service import sync_account_from_event

        account = event.get("data", {}).get("object", {})
        async with async_session_factory() as db:
            try:
                await sync_account_from_event(db, account)
                await db.commit()
            except Exception:
                logger.exception("stripe webhook: connect sync failed")
                await db.rollback()
                raise HTTPException(status_code=500, detail="Handler failed")

    elif event_type in (
        "customer.subscription.created",
        "customer.subscription.updated",
    ):
        # Platform-billing subscription events (Block 4). Marketplace
        # checkouts don't use subscriptions so this branch is
        # exclusively our own SaaS plan flow.
        from app.modules.commerce.payments.subscriptions.webhooks import handle_subscription_event

        sub_obj = event.get("data", {}).get("object", {})
        async with async_session_factory() as db:
            try:
                await handle_subscription_event(db, sub_obj)
                await db.commit()
            except Exception:
                logger.exception("stripe webhook: subscription sync failed")
                await db.rollback()
                raise HTTPException(status_code=500, detail="Handler failed")

    elif event_type == "customer.subscription.deleted":
        from app.modules.commerce.payments.subscriptions.webhooks import handle_subscription_deleted

        sub_obj = event.get("data", {}).get("object", {})
        async with async_session_factory() as db:
            try:
                await handle_subscription_deleted(db, sub_obj)
                await db.commit()
            except Exception:
                logger.exception("stripe webhook: subscription cancel failed")
                await db.rollback()
                raise HTTPException(status_code=500, detail="Handler failed")

    elif event_type == "invoice.payment_failed":
        from app.modules.commerce.payments.subscriptions.webhooks import (
            handle_invoice_payment_failed,
        )

        invoice = event.get("data", {}).get("object", {})
        async with async_session_factory() as db:
            try:
                await handle_invoice_payment_failed(db, invoice)
                await db.commit()
            except Exception:
                logger.exception("stripe webhook: invoice fail handler crashed")
                await db.rollback()
                raise HTTPException(status_code=500, detail="Handler failed")

    return JSONResponse({"received": True})
