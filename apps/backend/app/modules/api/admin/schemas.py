"""Pydantic schemas for the admin API."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

# ─── Templates ────────────────────────────────────────────────────────


class AdminTemplateRow(BaseModel):
    """Admin view of a template — includes draft/suspended/archived rows
    and the author's email so staff don't have to JOIN manually."""
    id: uuid.UUID
    slug: str
    title: str
    author_user_id: uuid.UUID
    author_email: str | None
    author_name: str
    status: str
    is_featured: bool
    price_cents: int
    fork_count: int
    rating_avg: Decimal | None
    rating_count: int
    created_at: datetime
    published_at: datetime | None


class TemplateModerationRequest(BaseModel):
    is_featured: bool | None = None
    status: str | None = Field(default=None, pattern="^(draft|published|suspended|archived)$")
    reason: str | None = Field(default=None, max_length=500)


# ─── Users ────────────────────────────────────────────────────────────


class AdminUserRow(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str | None
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login_at: datetime | None
    # Stripe Connect onboarding state — surfaced so staff can see at a
    # glance whether an author is configured to sell paid templates.
    stripe_account_id: str | None
    stripe_charges_enabled: bool
    stripe_payouts_enabled: bool


class UserBanRequest(BaseModel):
    is_active: bool
    reason: str | None = Field(default=None, max_length=500)


class GrantRoleRequest(BaseModel):
    role: str = Field(pattern="^(user|moderator|support|admin)$")


class PayoutSuspendRequest(BaseModel):
    """Admin override for an author's payout state.

    Setting ``enabled=False`` flips both ``stripe_charges_enabled`` and
    ``stripe_payouts_enabled`` to False — the author can no longer be
    paid for paid-template sales until they re-onboard. Setting it back
    to True restores ground truth from Stripe (we re-sync from the next
    ``account.updated`` event; explicit re-enable is rare and logged).
    """

    enabled: bool
    reason: str | None = Field(default=None, max_length=500)


# ─── Purchases ────────────────────────────────────────────────────────


class SettlePurchaseRequest(BaseModel):
    """Admin marks a paid purchase as settled with the author."""

    reference: str | None = Field(default=None, max_length=255)
    """Bank-transfer id / payout id / any external receipt staff want to keep."""


class AdminPurchaseRow(BaseModel):
    id: uuid.UUID
    buyer_user_id: uuid.UUID
    buyer_email: str | None
    template_id: uuid.UUID
    template_title: str | None
    price_paid_cents: int
    currency: str
    status: str
    provider: str
    provider_transaction_id: str | None
    purchased_at: datetime
    refunded_at: datetime | None
    settled_at: datetime | None
    settlement_reference: str | None


class RefundRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


# ─── Stats ────────────────────────────────────────────────────────────


class AdminStats(BaseModel):
    """Snapshot of platform-wide counters. Read-only."""
    total_users: int
    active_users_30d: int
    total_templates: int
    published_templates: int
    total_forks: int
    total_purchases_paid: int
    revenue_cents_30d: int
    revenue_cents_all_time: int


# ─── Audit log ────────────────────────────────────────────────────────


class AdminActionRow(BaseModel):
    id: uuid.UUID
    actor_user_id: uuid.UUID | None
    actor_email: str | None
    action: str
    target_type: str | None
    target_id: str | None
    details: dict
    created_at: datetime
