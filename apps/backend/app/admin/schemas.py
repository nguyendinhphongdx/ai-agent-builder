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


class UserBanRequest(BaseModel):
    is_active: bool
    reason: str | None = Field(default=None, max_length=500)


class GrantRoleRequest(BaseModel):
    role: str = Field(pattern="^(user|moderator|support|admin)$")


# ─── Purchases ────────────────────────────────────────────────────────


class AdminPurchaseRow(BaseModel):
    id: uuid.UUID
    buyer_user_id: uuid.UUID
    buyer_email: str | None
    template_id: uuid.UUID
    template_title: str | None
    price_paid_cents: int
    currency: str
    status: str
    stripe_payment_intent_id: str | None
    purchased_at: datetime
    refunded_at: datetime | None


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
