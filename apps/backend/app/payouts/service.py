"""Stripe Connect Express — author onboarding + status sync.

The platform creates one Express account per author (lazily, on first
``start_onboarding`` call). Stripe hosts the onboarding form;
we redirect the user there via an ``AccountLink``. After onboarding,
``account.updated`` events flow to our webhook and we mirror the
``charges_enabled`` / ``payouts_enabled`` flags onto the User row.
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.context import current_user_id
from app.models.user import User
from app.payments.providers.stripe import _stripe, is_stripe_configured

logger = logging.getLogger("agentforge")


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
    if not user.stripe_account_id:
        return {
            "connected": False,
            "charges_enabled": False,
            "payouts_enabled": False,
            "account_id": None,
        }
    return {
        "connected": True,
        "charges_enabled": user.stripe_charges_enabled,
        "payouts_enabled": user.stripe_payouts_enabled,
        "account_id": user.stripe_account_id,
    }


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
