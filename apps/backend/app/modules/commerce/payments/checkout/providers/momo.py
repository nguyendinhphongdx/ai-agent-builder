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

from app.models.agent import Agent
from app.models.agent_template import AgentTemplate
from app.models.agent_template_purchase import AgentTemplatePurchase
from app.models.agent_template_version import AgentTemplateVersion
from app.models.user import User
from app.modules.commerce.hub.snapshot import fork_snapshot_into_agent
from app.modules.commerce.payments.checkout.base import PaymentProvider
from app.platform.config import settings
from app.platform.context import current_user_id, reset_current_user_id, set_current_user_id
from app.platform.security.crypto import decrypt_secret

logger = logging.getLogger("agentforge")


def _sign(secret: str, raw: str) -> str:
    """HMAC-SHA256 hex digest — MoMo's signature scheme.

    The signed string format is fixed by MoMo and parameter order matters.
    Build it explicitly per call rather than auto-deriving from a dict
    (sorting alphabetically silently breaks signing).
    """
    return hmac.new(secret.encode(), raw.encode(), hashlib.sha256).hexdigest()


def _author_credentials(author: User) -> tuple[str, str, str] | None:
    """Return ``(partner_code, access_key, secret_key)`` for an author with
    a connected MoMo Business account, or ``None`` if they haven't connected.

    Falls back to platform-collects (`settings.MOMO_*`) at the call site.
    """
    if not (
        author.momo_partner_code
        and author.momo_access_key_enc
        and author.momo_secret_key_enc
    ):
        return None
    return (
        author.momo_partner_code,
        decrypt_secret(author.momo_access_key_enc),
        decrypt_secret(author.momo_secret_key_enc),
    )


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

        # Per-author Connect: if the template author has stored MoMo
        # merchant credentials, route the buyer's payment to *their*
        # MoMo balance. Falls back to platform-collects (settings.MOMO_*)
        # when the author hasn't connected — then ops settles them
        # out-of-band as before.
        author = await db.get(User, template.user_id)
        if author is None:
            raise RuntimeError("Template author missing")
        author_creds = _author_credentials(author)
        if author_creds is not None:
            partner_code, access_key, secret_key = author_creds
        elif self.is_configured():
            partner_code = settings.MOMO_PARTNER_CODE
            access_key = settings.MOMO_ACCESS_KEY
            secret_key = settings.MOMO_SECRET_KEY
        else:
            raise RuntimeError(
                "VND payments are unavailable — neither author nor platform has MoMo configured"
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
            f"accessKey={access_key}"
            f"&amount={amount_vnd}"
            f"&extraData={extra_data}"
            f"&ipnUrl={settings.MOMO_NOTIFY_URL}"
            f"&orderId={txn_id}"
            f"&orderInfo={order_info}"
            f"&partnerCode={partner_code}"
            f"&redirectUrl={settings.MOMO_RETURN_URL}"
            f"&requestId={txn_id}"
            f"&requestType=captureWallet"
        )
        body = {
            "partnerCode": partner_code,
            "accessKey": access_key,
            "requestId": txn_id,
            "orderId": txn_id,
            "amount": str(amount_vnd),
            "orderInfo": order_info,
            "redirectUrl": settings.MOMO_RETURN_URL,
            "ipnUrl": settings.MOMO_NOTIFY_URL,
            "requestType": "captureWallet",
            "extraData": extra_data,
            "lang": "vi",
            "signature": _sign(secret_key, raw),
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

    async def refund(
        self,
        db: AsyncSession,
        purchase: AgentTemplatePurchase,
        *,
        reason: str | None = None,
    ) -> None:
        """Refund via MoMo's `/v2/gateway/api/refund` endpoint.

        Requires the ``transId`` MoMo issued at payment time — we stash
        it on the Purchase row when handling the IPN. A fresh ``requestId``
        per refund call (uuid4) is needed for idempotency on MoMo's side.
        """
        if not purchase.provider_transaction_id:
            raise ValueError("Purchase has no MoMo transaction id to refund")

        # Refund against the same merchant the original charge ran through —
        # author-Connect rows refund from the author's MoMo account, platform
        # rows from the platform's. Look up the template author from the
        # Purchase row.
        template = await db.get(AgentTemplate, purchase.template_id)
        author = await db.get(User, template.user_id) if template else None
        author_creds = _author_credentials(author) if author else None
        if author_creds is not None:
            partner_code, access_key, secret_key = author_creds
        elif self.is_configured():
            partner_code = settings.MOMO_PARTNER_CODE
            access_key = settings.MOMO_ACCESS_KEY
            secret_key = settings.MOMO_SECRET_KEY
        else:
            raise RuntimeError(
                "MoMo not configured — neither author nor platform credentials available"
            )

        # MoMo identifies the original payment by its `transId`. We replaced
        # `provider_transaction_id` with that id when we received the IPN.
        trans_id = purchase.provider_transaction_id
        amount = purchase.price_paid_cents
        request_id = str(uuid.uuid4())
        # MoMo wants `orderId` to be a fresh value distinct from the
        # original — pattern is to suffix the original to keep traceability.
        refund_order_id = f"refund-{purchase.id}"
        description = (reason or "Buyer refund")[:200]

        raw = (
            f"accessKey={access_key}"
            f"&amount={amount}"
            f"&description={description}"
            f"&orderId={refund_order_id}"
            f"&partnerCode={partner_code}"
            f"&requestId={request_id}"
            f"&transId={trans_id}"
        )
        body = {
            "partnerCode": partner_code,
            "accessKey": access_key,
            "requestId": request_id,
            "orderId": refund_order_id,
            "amount": str(amount),
            "transId": trans_id,
            "description": description,
            "lang": "vi",
            "signature": _sign(secret_key, raw),
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.post(
                    f"{settings.MOMO_ENDPOINT}/v2/gateway/api/refund", json=body
                )
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPError as exc:
                raise RuntimeError(f"MoMo refund failed: {exc}") from exc

        # MoMo returns resultCode=0 on success. Anything else is a
        # business-level failure (already refunded, exceeds amount, etc.)
        # — surface the message so the admin can act on it.
        if data.get("resultCode") != 0:
            raise RuntimeError(
                f"MoMo refund rejected: code={data.get('resultCode')} "
                f"msg={data.get('message')}"
            )

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


async def resolve_ipn_credentials(
    db: AsyncSession, payload: dict[str, Any]
) -> tuple[str, str] | None:
    """Pick the (access_key, secret_key) MoMo would have signed this IPN with.

    Per-author connect: the IPN's orderId is the txn we issued, which
    points back to a Purchase → Template → author. If the author has
    connected their own MoMo merchant we use their creds; otherwise
    fall back to platform creds. Returns ``None`` when neither set is
    available (e.g. unknown orderId + platform unconfigured).
    """
    order_id = payload.get("orderId")
    if order_id:
        # `orderId` matches `provider_transaction_id` *until* we replace
        # it with `transId` post-IPN — IPN arrives before that swap, so
        # this lookup is reliable for fresh IPNs but may miss on retries
        # of a row we already processed (which is a no-op anyway).
        result = await db.execute(
            select(AgentTemplatePurchase).where(
                AgentTemplatePurchase.provider == "momo",
                AgentTemplatePurchase.provider_transaction_id == order_id,
            ).limit(1)
        )
        purchase = result.scalar_one_or_none()
        if purchase is not None:
            template = await db.get(AgentTemplate, purchase.template_id)
            author = await db.get(User, template.user_id) if template else None
            author_creds = _author_credentials(author) if author else None
            if author_creds is not None:
                _, access_key, secret_key = author_creds
                return access_key, secret_key

    if settings.MOMO_ACCESS_KEY and settings.MOMO_SECRET_KEY:
        return settings.MOMO_ACCESS_KEY, settings.MOMO_SECRET_KEY
    return None


def verify_ipn_signature(
    payload: dict[str, Any], access_key: str, secret_key: str
) -> bool:
    """Verify HMAC-SHA256 on a MoMo IPN payload against the supplied
    access/secret pair (resolved via :func:`resolve_ipn_credentials`).

    Param order is fixed by MoMo's IPN contract — see their docs.
    Returns False on any mismatch / missing field rather than raising,
    so the caller maps cleanly to a 400.
    """
    sig = payload.get("signature")
    if not sig:
        return False
    raw = (
        f"accessKey={access_key}"
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
    expected = _sign(secret_key, raw)
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
