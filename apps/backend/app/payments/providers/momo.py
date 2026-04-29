"""MoMo Checkout — `PaymentProvider` implementation for VND payments.

Buyer-side flow mirrors :class:`StripeProvider`:
  1. POST /api/templates/{id}/purchase  (template.currency == "VND")
       └─ MoMo `create` API → redirect URL + Purchase(status=pending)
  2. Browser redirects to MoMo's hosted payment page
  3. Buyer pays via QR / e-wallet / linked card
  4. MoMo POSTs IPN to /api/webhooks/momo (HMAC-SHA256 signature verified)
       └─ mark Purchase paid → fork agent in background
  5. MoMo redirects browser to MOMO_RETURN_URL (FE polls /purchase-status)

MoMo-specific concerns:
  - VND only — no currency conversion. Templates priced in VND go here.
  - No author payouts in V1 (MoMo has no Connect equivalent). Platform
    collects all funds, settles with authors out-of-band. The Connect
    onboarding gate that StripeProvider applies is bypassed here.
  - Signature scheme: HMAC-SHA256 over a fixed param-order string. We
    sign on outbound `create` requests and verify on inbound IPN.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import uuid
from typing import Any, ClassVar

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.context import current_user_id, reset_current_user_id, set_current_user_id
from app.hub.snapshot import fork_snapshot_into_agent
from app.models.agent import Agent
from app.models.agent_template import AgentTemplate
from app.models.agent_template_purchase import AgentTemplatePurchase
from app.models.agent_template_version import AgentTemplateVersion
from app.payments.base import PaymentProvider

logger = logging.getLogger("agentforge")


def _sign(secret: str, raw: str) -> str:
    """HMAC-SHA256 hex digest — MoMo's signature scheme.

    The signed string format is fixed by MoMo and parameter order matters.
    Build it explicitly per call rather than auto-deriving from a dict
    (sorting alphabetically silently breaks signing).
    """
    return hmac.new(secret.encode(), raw.encode(), hashlib.sha256).hexdigest()


class MoMoProvider(PaymentProvider):
    """MoMo Vietnam — VND-locked e-wallet checkout."""

    name: ClassVar[str] = "momo"

    @classmethod
    def is_configured(cls) -> bool:
        return bool(
            settings.MOMO_PARTNER_CODE
            and settings.MOMO_ACCESS_KEY
            and settings.MOMO_SECRET_KEY
        )

    async def create_checkout(
        self, db: AsyncSession, template_id: uuid.UUID
    ) -> tuple[str, AgentTemplatePurchase]:
        if not self.is_configured():
            raise RuntimeError("VND payments are unavailable — MoMo not configured")

        user_id = current_user_id()
        template = await db.get(AgentTemplate, template_id)
        if template is None or template.status != "published":
            raise ValueError("Template not found or not published")
        if template.price_cents <= 0:
            raise ValueError("Template is free — call /fork instead of /purchase")
        if template.currency.upper() != "VND":
            raise ValueError(
                f"Template is priced in {template.currency} — use the Stripe path"
            )

        existing_paid = await db.execute(
            select(AgentTemplatePurchase).where(
                AgentTemplatePurchase.buyer_id == user_id,
                AgentTemplatePurchase.template_id == template_id,
                AgentTemplatePurchase.status == "paid",
            ).limit(1)
        )
        if existing_paid.scalar_one_or_none() is not None:
            raise ValueError("You already own this template — fork it from your library")

        version_result = await db.execute(
            select(AgentTemplateVersion).where(
                AgentTemplateVersion.template_id == template_id,
                AgentTemplateVersion.is_current == True,  # noqa: E712
            ).limit(1)
        )
        version = version_result.scalar_one_or_none()
        if version is None:
            raise RuntimeError(f"Template {template_id} has no current version")

        # MoMo prices are whole VND. We co-opt `price_cents` for VND too —
        # it's a misnomer at this point but the column is documented here.
        amount_vnd = template.price_cents

        txn_id = str(uuid.uuid4())
        order_info = f"AgentForge fork: {template.title[:80]}"
        extra_data = json.dumps(
            {
                "template_id": str(template_id),
                "version_id": str(version.id),
                "buyer_id": str(user_id),
            }
        )

        raw = (
            f"accessKey={settings.MOMO_ACCESS_KEY}"
            f"&amount={amount_vnd}"
            f"&extraData={extra_data}"
            f"&ipnUrl={settings.MOMO_NOTIFY_URL}"
            f"&orderId={txn_id}"
            f"&orderInfo={order_info}"
            f"&partnerCode={settings.MOMO_PARTNER_CODE}"
            f"&redirectUrl={settings.MOMO_RETURN_URL}"
            f"&requestId={txn_id}"
            f"&requestType=captureWallet"
        )
        body = {
            "partnerCode": settings.MOMO_PARTNER_CODE,
            "accessKey": settings.MOMO_ACCESS_KEY,
            "requestId": txn_id,
            "orderId": txn_id,
            "amount": str(amount_vnd),
            "orderInfo": order_info,
            "redirectUrl": settings.MOMO_RETURN_URL,
            "ipnUrl": settings.MOMO_NOTIFY_URL,
            "requestType": "captureWallet",
            "extraData": extra_data,
            "lang": "vi",
            "signature": _sign(settings.MOMO_SECRET_KEY, raw),
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{settings.MOMO_ENDPOINT}/v2/gateway/api/create", json=body
            )
            resp.raise_for_status()
            data = resp.json()

        if data.get("resultCode") != 0 or not data.get("payUrl"):
            raise RuntimeError(
                f"MoMo create failed: code={data.get('resultCode')} "
                f"msg={data.get('message')}"
            )

        purchase = AgentTemplatePurchase(
            buyer_id=user_id,
            template_id=template_id,
            version_id=version.id,
            price_paid_cents=amount_vnd,
            currency="VND",
            status="pending",
            provider=self.name,
            provider_transaction_id=txn_id,
        )
        db.add(purchase)
        await db.flush()
        await db.refresh(purchase)
        return data["payUrl"], purchase

    async def get_purchase_status(
        self, db: AsyncSession, txn_id: str
    ) -> dict[str, Any] | None:
        user_id = current_user_id()
        result = await db.execute(
            select(AgentTemplatePurchase).where(
                AgentTemplatePurchase.provider == self.name,
                AgentTemplatePurchase.provider_transaction_id == txn_id,
                AgentTemplatePurchase.buyer_id == user_id,
            ).limit(1)
        )
        purchase = result.scalar_one_or_none()
        if purchase is None:
            return None

        agent_id: uuid.UUID | None = None
        if purchase.status == "paid":
            agent_result = await db.execute(
                select(Agent.id).where(
                    Agent.user_id == user_id,
                    Agent.template_id == purchase.template_id,
                    Agent.template_version_id == purchase.version_id,
                ).order_by(Agent.created_at.desc()).limit(1)
            )
            agent_id = agent_result.scalar_one_or_none()
        return {
            "status": purchase.status,
            "provider": self.name,
            "template_id": str(purchase.template_id),
            "agent_id": str(agent_id) if agent_id else None,
        }


# ─── Webhook signature + event handler — called by `webhooks.momo` ────


def verify_ipn_signature(payload: dict[str, Any]) -> bool:
    """Verify HMAC-SHA256 on a MoMo IPN payload.

    Param order is fixed by MoMo's IPN contract — see their docs.
    Returns False on any mismatch / missing field rather than raising,
    so the caller maps cleanly to a 400.
    """
    sig = payload.get("signature")
    if not sig:
        return False
    raw = (
        f"accessKey={settings.MOMO_ACCESS_KEY}"
        f"&amount={payload.get('amount', '')}"
        f"&extraData={payload.get('extraData', '')}"
        f"&message={payload.get('message', '')}"
        f"&orderId={payload.get('orderId', '')}"
        f"&orderInfo={payload.get('orderInfo', '')}"
        f"&orderType={payload.get('orderType', '')}"
        f"&partnerCode={payload.get('partnerCode', '')}"
        f"&payType={payload.get('payType', '')}"
        f"&requestId={payload.get('requestId', '')}"
        f"&responseTime={payload.get('responseTime', '')}"
        f"&resultCode={payload.get('resultCode', '')}"
        f"&transId={payload.get('transId', '')}"
    )
    expected = _sign(settings.MOMO_SECRET_KEY, raw)
    return hmac.compare_digest(expected, sig)


async def handle_ipn(db: AsyncSession, payload: dict[str, Any]) -> Agent | None:
    """Mark Purchase paid + fork the template (idempotent)."""
    if payload.get("resultCode") != 0:
        logger.info(
            f"momo ipn: non-zero resultCode={payload.get('resultCode')} "
            f"order={payload.get('orderId')}"
        )
        return None

    order_id = payload.get("orderId")
    if not order_id:
        return None

    result = await db.execute(
        select(AgentTemplatePurchase).where(
            AgentTemplatePurchase.provider == "momo",
            AgentTemplatePurchase.provider_transaction_id == order_id,
        ).limit(1)
    )
    purchase = result.scalar_one_or_none()
    if purchase is None:
        logger.info(f"momo ipn: purchase row not found for order {order_id}")
        return None
    if purchase.status == "paid":
        return None

    purchase.status = "paid"
    if (trans_id := payload.get("transId")):
        purchase.provider_transaction_id = str(trans_id)
    await db.flush()

    extra = json.loads(payload.get("extraData") or "{}")
    template_id = uuid.UUID(extra["template_id"])
    version_id = uuid.UUID(extra["version_id"])
    buyer_id = uuid.UUID(extra["buyer_id"])

    token = set_current_user_id(buyer_id)
    try:
        version = await db.get(AgentTemplateVersion, version_id)
        if version is None:
            logger.error(f"momo ipn: version {version_id} disappeared")
            return None
        agent = await fork_snapshot_into_agent(
            db, version.snapshot, template_id=template_id, version_id=version_id
        )
    finally:
        reset_current_user_id(token)

    await db.execute(
        update(AgentTemplate)
        .where(AgentTemplate.id == template_id)
        .values(fork_count=AgentTemplate.fork_count + 1)
    )
    await db.flush()

    logger.info(
        f"momo ipn: forked template={template_id} version={version_id} "
        f"buyer={buyer_id} → agent={agent.id}"
    )
    return agent
