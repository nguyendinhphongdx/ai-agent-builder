"""Schemas for ``/api/system/*`` — keep separate from the public
``OrganizationResponse`` so we can expose extra counters / billing
fields that customers shouldn't see on their own org payload."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SystemOrgRow(BaseModel):
    """Row in the platform-admin org table."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    plan: str
    billing_email: str | None
    is_system: bool
    member_count: int
    workspace_count: int
    created_at: datetime


class SystemOrgDetail(SystemOrgRow):
    """Full org detail — adds settings + recent members."""

    settings: dict
    owner_email: str | None


class SystemOrgCreate(BaseModel):
    """Create an org on behalf of a customer. The platform admin assigns
    the first owner by email — that user must already exist."""

    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(
        min_length=2,
        max_length=64,
        pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$",
    )
    owner_email: EmailStr
    billing_email: EmailStr | None = None
    plan: str | None = None


class SystemOrgPatch(BaseModel):
    """Platform-admin override. Any field can be omitted to leave it."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    plan: str | None = None
    billing_email: EmailStr | None = None
    settings: dict | None = None


# ─── Subscriptions ────────────────────────────────────────────────


class SystemSubscriptionRow(BaseModel):
    """Row in ``/system/subscriptions``. Joins org + sub for one-shot display."""

    model_config = ConfigDict(from_attributes=True)

    org_id: uuid.UUID
    org_name: str
    org_slug: str
    plan_code: str
    status: str
    is_live: bool
    current_period_end: datetime | None
    cancel_at_period_end: bool
    stripe_subscription_id: str | None
    created_at: datetime


class SystemSubscriptionStats(BaseModel):
    """Aggregate billing snapshot — single tile in the admin header."""

    total_orgs: int
    live_subs: int
    by_status: dict[str, int]          # status → count
    by_plan: dict[str, int]            # plan_code → count
    trialing: int
    cancel_scheduled: int               # cancel_at_period_end = true


class SystemSubscriptionSetPlan(BaseModel):
    plan_code: str = Field(min_length=1, max_length=32)


class SystemSubscriptionCancel(BaseModel):
    """Body for cancel — defaults to end-of-period (don't yank live users)."""

    immediate: bool = False


# ─── Packages (read-only PLANS catalogue) ─────────────────────────


class SystemPackageRow(BaseModel):
    """One plan in the comparison matrix. ``active_orgs`` is the count
    of orgs currently *resolved* to this plan (live sub OR org.plan
    fallback)."""

    code: str
    name: str
    monthly_llm_tokens: int             # 0 = unlimited
    monthly_kb_queries: int             # 0 = unlimited
    max_workspaces: int                 # 0 = unlimited
    max_members: int                    # 0 = unlimited
    features: dict[str, bool | int]
    stripe_price_id: str | None
    stripe_metered_price_id: str | None
    is_self_serve: bool
    active_orgs: int


# ─── Payment providers ────────────────────────────────────────────


class SystemPaymentProviderUpsert(BaseModel):
    """Body for create/update of a payment-provider config row.

    ``secrets`` semantics:
      - ``None``  → keep existing secrets untouched (admin only edited
                    non-secret config).
      - ``{}``    → clear all secrets.
      - non-empty → replace the secrets blob with this dict.
    """

    display_name: str = Field(min_length=1, max_length=64)
    kind: str = Field(default="both", pattern=r"^(free|paid|both)$")
    is_enabled: bool = False
    is_test_mode: bool = True
    secrets: dict[str, str] | None = None
    config: dict | None = None
    description: str | None = None
