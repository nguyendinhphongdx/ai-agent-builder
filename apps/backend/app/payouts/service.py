"""Author payouts.

- **Stripe Connect Express onboarding** (``start_onboarding``,
  ``get_status``, ``create_dashboard_link``, ``sync_account_from_event``).
  Lazily creates an Express account, hosts onboarding via AccountLink,
  mirrors ``charges_enabled`` / ``payouts_enabled`` from the
  ``account.updated`` webhook onto the User row.
- **Payment history** (``list_history``, ``get_summary``). Author-side
  view of purchases of templates they own. Stripe gross deducts the
  platform fee (computed deterministically from
  ``STRIPE_PLATFORM_FEE_BPS``); MoMo is platform-collects so net = gross.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.context import current_user_id
from app.models.agent_template import AgentTemplate
from app.models.agent_template_purchase import AgentTemplatePurchase
from app.models.user import User
from app.payments.providers.stripe import _stripe, is_stripe_configured
from app.security.crypto import encrypt_secret, mask_secret

logger = logging.getLogger("agentforge")


def _platform_fee_cents(price_cents: int, provider: str) -> int:
    """Deterministic platform fee — must match what Stripe collects on
    the actual charge (`application_fee_amount` in the Checkout call).

    MoMo currently has no platform-side fee on the charge; we settle
    authors out-of-band, so net = gross from the author's perspective.
    """
    if provider == "stripe":
        return (price_cents * settings.STRIPE_PLATFORM_FEE_BPS) // 10_000
    return 0


def can_receive_payouts(user: User) -> bool:
    """True when the author is onboarded enough to be paid for sales."""
    return bool(
        user.stripe_account_id
        and user.stripe_charges_enabled
        and user.stripe_payouts_enabled
    )


async def _get_user_strict(db: AsyncSession) -> User:
    user = await db.get(User, current_user_id())
    if user is None:
        raise RuntimeError("Authenticated user vanished mid-request")
    return user


async def start_onboarding(db: AsyncSession) -> str:
    """Create (or reuse) an Express account for the current user and return
    the URL of a fresh onboarding AccountLink.

    AccountLinks are single-use + short-lived, so we mint a new one on
    every call. The frontend opens the URL in a new tab and polls
    ``/me/payouts/status`` until ``charges_enabled`` flips.
    """
    if not is_stripe_configured():
        raise RuntimeError("Stripe Connect not configured")
    if not (settings.STRIPE_CONNECT_RETURN_URL and settings.STRIPE_CONNECT_REFRESH_URL):
        raise RuntimeError(
            "STRIPE_CONNECT_RETURN_URL and STRIPE_CONNECT_REFRESH_URL must be set"
        )

    stripe = _stripe()
    user = await _get_user_strict(db)

    if not user.stripe_account_id:
        # `controller` mode controls who pays Stripe fees, owns the
        # dashboard, and handles disputes. "application" = platform pays
        # fees and owns the dashboard (Express). The author signs up with
        # minimal effort.
        account = stripe.Account.create(
            type="express",
            email=user.email,
            capabilities={
                "transfers": {"requested": True},
                "card_payments": {"requested": True},
            },
            business_type="individual",
            metadata={"user_id": str(user.id)},
        )
        user.stripe_account_id = account.id
        await db.flush()
        logger.info(f"stripe connect: created account {account.id} for user {user.id}")

    link = stripe.AccountLink.create(
        account=user.stripe_account_id,
        refresh_url=settings.STRIPE_CONNECT_REFRESH_URL,
        return_url=settings.STRIPE_CONNECT_RETURN_URL,
        type="account_onboarding",
    )
    return link.url


async def get_status(db: AsyncSession) -> dict[str, Any]:
    """Return the cached onboarding status for the current user.

    Cheap — reads the User row only. The webhook keeps it in sync. Callers
    that need ground truth (e.g. the publish-paid gate) should use this; if
    truly nothing is cached yet we fall back to a Stripe round-trip.
    """
    user = await _get_user_strict(db)
    momo_connected = bool(
        user.momo_partner_code and user.momo_access_key_enc and user.momo_secret_key_enc
    )
    if not user.stripe_account_id:
        return {
            "connected": False,
            "charges_enabled": False,
            "payouts_enabled": False,
            "account_id": None,
            "momo_connected": momo_connected,
            "momo_partner_code": user.momo_partner_code,
        }
    return {
        "connected": True,
        "charges_enabled": user.stripe_charges_enabled,
        "payouts_enabled": user.stripe_payouts_enabled,
        "account_id": user.stripe_account_id,
        "momo_connected": momo_connected,
        "momo_partner_code": user.momo_partner_code,
    }


# ─── MoMo per-author connect ──────────────────────────────────────────


async def connect_momo(
    db: AsyncSession,
    *,
    partner_code: str,
    access_key: str,
    secret_key: str,
) -> dict[str, Any]:
    """Save the author's MoMo Business merchant credentials. Encrypted at
    rest with the same Fernet key that protects ai_credentials.

    No round-trip to MoMo to validate — they have no test endpoint for
    "are these credentials live". The first real checkout call will fail
    fast with a clear `MoMo create failed: code=…` if the trio is wrong,
    and the author can re-paste.
    """
    user = await _get_user_strict(db)
    user.momo_partner_code = partner_code.strip()
    user.momo_access_key_enc = encrypt_secret(access_key.strip())
    user.momo_secret_key_enc = encrypt_secret(secret_key.strip())
    await db.flush()
    return {
        "connected": True,
        "partner_code": user.momo_partner_code,
        "access_key_masked": mask_secret(access_key.strip()),
    }


async def disconnect_momo(db: AsyncSession) -> None:
    """Forget the author's MoMo credentials. Future VND checkouts on
    their templates fall back to platform-collects."""
    user = await _get_user_strict(db)
    user.momo_partner_code = None
    user.momo_access_key_enc = None
    user.momo_secret_key_enc = None
    await db.flush()


async def create_dashboard_link(db: AsyncSession) -> str:
    """Generate a one-time login URL for the author's Stripe Express dashboard.

    The author manages payouts, taxes, and disputes there — we never touch
    that data ourselves. Empty / not-yet-connected → caller maps to 400.
    """
    if not is_stripe_configured():
        raise RuntimeError("Stripe Connect not configured")
    user = await _get_user_strict(db)
    if not user.stripe_account_id:
        raise ValueError("No Stripe account — start onboarding first")
    if not user.stripe_charges_enabled:
        raise ValueError("Onboarding not complete — finish the Connect form first")

    stripe = _stripe()
    link = stripe.Account.create_login_link(user.stripe_account_id)
    return link.url


# ─── Webhook sync (account.updated) ───────────────────────────────────


# ─── Author payment history ───────────────────────────────────────────


async def list_history(
    db: AsyncSession,
    *,
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
    provider: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Paginated list of paid purchases for templates the user owns.

    Returns ``(items, total)``. Item rows include a computed
    ``platform_fee_cents`` and ``net_cents`` so the FE doesn't have to
    duplicate the fee math.

    Free purchases (``price_paid_cents == 0``) are excluded — they don't
    represent revenue.
    """
    user_id = current_user_id()

    base = (
        select(AgentTemplatePurchase, AgentTemplate.title, User.email)
        .join(AgentTemplate, AgentTemplate.id == AgentTemplatePurchase.template_id)
        .join(User, User.id == AgentTemplatePurchase.buyer_id)
        .where(AgentTemplate.user_id == user_id)
        .where(AgentTemplatePurchase.price_paid_cents > 0)
    )
    if status:
        base = base.where(AgentTemplatePurchase.status == status)
    if provider:
        base = base.where(AgentTemplatePurchase.provider == provider)

    count_q = (
        select(func.count())
        .select_from(AgentTemplatePurchase)
        .join(AgentTemplate, AgentTemplate.id == AgentTemplatePurchase.template_id)
        .where(AgentTemplate.user_id == user_id)
        .where(AgentTemplatePurchase.price_paid_cents > 0)
    )
    if status:
        count_q = count_q.where(AgentTemplatePurchase.status == status)
    if provider:
        count_q = count_q.where(AgentTemplatePurchase.provider == provider)

    total = (await db.execute(count_q)).scalar_one()

    rows = await db.execute(
        base.order_by(desc(AgentTemplatePurchase.purchased_at))
        .limit(limit)
        .offset(offset)
    )

    items: list[dict[str, Any]] = []
    for purchase, template_title, buyer_email in rows.all():
        fee = _platform_fee_cents(purchase.price_paid_cents, purchase.provider)
        items.append(
            {
                "id": str(purchase.id),
                "template_id": str(purchase.template_id),
                "template_title": template_title,
                # Mask the local-part for privacy — staff can pull full
                # email from /admin/purchases if needed for support.
                "buyer_email_masked": _mask_email(buyer_email),
                "price_paid_cents": purchase.price_paid_cents,
                "currency": purchase.currency,
                "platform_fee_cents": fee,
                "net_cents": purchase.price_paid_cents - fee,
                "provider": purchase.provider,
                "status": purchase.status,
                "purchased_at": purchase.purchased_at.isoformat()
                if purchase.purchased_at
                else None,
                "refunded_at": purchase.refunded_at.isoformat()
                if purchase.refunded_at
                else None,
                "settled_at": purchase.settled_at.isoformat()
                if purchase.settled_at
                else None,
            }
        )

    return items, total


def _mask_email(email: str | None) -> str | None:
    if not email or "@" not in email:
        return email
    local, _, domain = email.partition("@")
    if len(local) <= 2:
        return f"{local[0]}***@{domain}"
    return f"{local[0]}***{local[-1]}@{domain}"


async def get_summary(db: AsyncSession) -> dict[str, Any]:
    """Monthly + total revenue aggregates for the current user.

    Groups by ``(year-month, currency)`` so cross-currency rows stay
    distinct (we don't convert across currencies). Net is computed after
    the platform fee is deducted.
    """
    user_id = current_user_id()

    rows = await db.execute(
        select(
            func.date_trunc("month", AgentTemplatePurchase.purchased_at).label("month"),
            AgentTemplatePurchase.currency,
            AgentTemplatePurchase.provider,
            func.count().label("count"),
            func.coalesce(func.sum(AgentTemplatePurchase.price_paid_cents), 0).label(
                "gross"
            ),
        )
        .join(AgentTemplate, AgentTemplate.id == AgentTemplatePurchase.template_id)
        .where(AgentTemplate.user_id == user_id)
        .where(AgentTemplatePurchase.status == "paid")
        .where(AgentTemplatePurchase.price_paid_cents > 0)
        .group_by("month", AgentTemplatePurchase.currency, AgentTemplatePurchase.provider)
        .order_by(desc("month"))
    )

    by_month: dict[tuple[str, str], dict[str, int]] = defaultdict(
        lambda: {"gross": 0, "fees": 0, "net": 0, "count": 0}
    )
    by_currency: dict[str, dict[str, int]] = defaultdict(
        lambda: {"gross": 0, "fees": 0, "net": 0, "count": 0}
    )

    for month, currency, provider, count, gross in rows.all():
        cur = (currency or "USD").upper()
        # `month` is a Postgres timestamp at the start of the month; format
        # as "YYYY-MM" for the FE. Defensive isinstance for older drivers.
        if isinstance(month, datetime):
            month_key = month.strftime("%Y-%m")
        else:
            month_key = str(month)[:7]

        fee = _platform_fee_cents(int(gross or 0), provider)

        bucket_m = by_month[(month_key, cur)]
        bucket_m["count"] += count
        bucket_m["gross"] += int(gross or 0)
        bucket_m["fees"] += fee
        bucket_m["net"] += int(gross or 0) - fee

        bucket_c = by_currency[cur]
        bucket_c["count"] += count
        bucket_c["gross"] += int(gross or 0)
        bucket_c["fees"] += fee
        bucket_c["net"] += int(gross or 0) - fee

    return {
        "by_month": [
            {
                "month": m,
                "currency": c,
                "gross_cents": v["gross"],
                "fees_cents": v["fees"],
                "net_cents": v["net"],
                "count": v["count"],
            }
            for (m, c), v in sorted(by_month.items(), key=lambda x: (x[0][0], x[0][1]), reverse=True)
        ],
        "totals": [
            {
                "currency": c,
                "gross_cents": v["gross"],
                "fees_cents": v["fees"],
                "net_cents": v["net"],
                "count": v["count"],
            }
            for c, v in sorted(by_currency.items())
        ],
    }


# ─── Webhook sync (account.updated) ───────────────────────────────────


async def sync_account_from_event(db: AsyncSession, account: dict[str, Any]) -> None:
    """Mirror a Stripe ``account.updated`` event onto the User row.

    Idempotent — same payload re-applies the same flags. Unknown account
    ids (manual deletion in dashboard, etc.) are logged + ignored.
    """
    account_id = account.get("id")
    if not account_id:
        return

    result = await db.execute(
        select(User).where(User.stripe_account_id == account_id).limit(1)
    )
    user = result.scalar_one_or_none()
    if user is None:
        logger.warning(
            f"stripe connect webhook: account {account_id} not linked to any user"
        )
        return

    user.stripe_charges_enabled = bool(account.get("charges_enabled"))
    user.stripe_payouts_enabled = bool(account.get("payouts_enabled"))
    await db.flush()
    logger.info(
        f"stripe connect: synced account {account_id} for user {user.id} "
        f"(charges={user.stripe_charges_enabled} payouts={user.stripe_payouts_enabled})"
    )
