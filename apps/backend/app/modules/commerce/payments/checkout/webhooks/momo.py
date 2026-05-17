"""MoMo IPN (Instant Payment Notification) receiver.

MoMo's IPN is a JSON POST with a `signature` field; we verify it and
dispatch to the same fork-on-paid handler the redirect-side polling
relies on. MoMo retries non-2xx like Stripe does.

Per-author MoMo connect: when an author has connected their own MoMo
merchant account, the IPN comes signed with *their* secret. We resolve
the right secret from the Purchase row before verifying, falling back
to platform creds when the author hasn't connected.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.modules.commerce.payments.checkout.providers.momo import (
    MoMoProvider,
    handle_ipn,
    resolve_ipn_credentials,
    verify_ipn_signature,
)
from app.platform.db.session import async_session_factory

logger = logging.getLogger("agentforge")

router = APIRouter(prefix="/webhooks/momo", tags=["webhooks"])


@router.post("")
async def momo_ipn(request: Request):
    # Honest 404 only when the platform isn't configured at all.
    # `resolve_ipn_credentials` below also tries per-author Connect, so
    # an unconfigured platform with at least one connected author still
    # accepts that author's IPNs through that branch — but if `MoMoProvider`
    # is enabled, we accept up front and let credential resolution do the
    # per-row decision.
    if not await MoMoProvider.is_configured():
        raise HTTPException(status_code=404, detail="MoMo webhook not configured")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Expected JSON object")

    async with async_session_factory() as db:
        creds = await resolve_ipn_credentials(db, payload)
        if creds is None:
            logger.warning(
                f"momo ipn: no credentials available for order {payload.get('orderId')}"
            )
            raise HTTPException(status_code=400, detail="No credentials configured")

        access_key, secret_key = creds
        if not verify_ipn_signature(payload, access_key, secret_key):
            logger.warning(f"momo ipn: bad signature for order {payload.get('orderId')}")
            raise HTTPException(status_code=400, detail="Invalid signature")

        logger.info(
            f"momo ipn: order={payload.get('orderId')} "
            f"resultCode={payload.get('resultCode')}"
        )

        try:
            await handle_ipn(db, payload)
            await db.commit()
        except Exception:
            logger.exception("momo ipn: handler failed")
            await db.rollback()
            raise HTTPException(status_code=500, detail="Handler failed")

    # MoMo expects a 204 / 200; their docs say either is fine.
    return JSONResponse({"received": True})
