"""Pydantic schemas for the billing API.

Shape mirrors what the FE needs for the billing dashboard:
  - PlanInfo for the plan picker on the upgrade page
  - SubscriptionInfo for the "you are on" card
  - QuotaUsage for the progress bars
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class PlanInfo(BaseModel):
    """Public-facing view of a Plan — quotas + feature flags."""

    code: str
    name: str
    monthly_llm_tokens: int  # 0 = unlimited
    monthly_kb_queries: int
    max_workspaces: int
    max_members: int
    features: dict[str, bool | int]
    # Set iff the plan has a configured Stripe price — controls the
    # FE upgrade button. Enterprise without env-mapped price → hidden.
    is_self_serve: bool


class SubscriptionInfo(BaseModel):
    plan: PlanInfo
    status: str  # active | trialing | past_due | canceled | none
    current_period_start: datetime | None
    current_period_end: datetime | None
    cancel_at_period_end: bool
    # When True, this org has never spoken to Stripe. The free-tier
    # quota still applies; FE renders "Upgrade" instead of "Manage".
    has_stripe_subscription: bool


class QuotaUsage(BaseModel):
    """Current-period usage / limit pair, ready for a progress bar."""

    used: int
    limit: int  # 0 = unlimited
    pct: float  # used / limit * 100, capped at 100 for chart sanity


class BillingOverview(BaseModel):
    subscription: SubscriptionInfo
    tokens: QuotaUsage
    kb_queries: QuotaUsage
