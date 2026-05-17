"""Plan catalogue — quotas + feature flags per tier.

Declared in code (not DB) so plan rollout is a deploy not a migration:
adding a "team" tier is a dataclass entry and a Stripe price-id env
var, no schema change.

Two layers:
  - ``Plan`` dataclass: declarative shape — quotas, feature flags,
    Stripe price-id keys (resolved against settings at call time so
    test vs prod price ids don't pollute git history).
  - ``PLANS``: the registry. Lookup is by code string ("free", …).

Resolution order for "what tier is this org on":
  1. ``OrgSubscription`` row, if live (active / trialing / past_due).
  2. Otherwise the ``organizations.plan`` column (legacy + free seed).
  3. Otherwise hard-default ``free``.

The Plan object answers "what can this org do now?" — quota
amounts and feature booleans both live here so callers have one
import.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.platform.config import settings

UNLIMITED = 0  # sentinel — quota check treats 0 as "no cap"

PLAN_FREE = "free"
PLAN_STARTER = "starter"
PLAN_PRO = "pro"
PLAN_ENTERPRISE = "enterprise"


@dataclass(frozen=True)
class Plan:
    code: str
    name: str
    # Hard quotas — enforced by quota guards before each billable op.
    monthly_llm_tokens: int
    monthly_kb_queries: int
    # Soft quotas — checked at create-time, not per-request.
    max_workspaces: int
    max_members: int
    # Feature gates — looked up via ``Plan.has_feature(name)``.
    features: dict[str, bool | int] = field(default_factory=dict)
    # Settings attribute that holds the Stripe price for the base
    # (recurring) subscription. ``""`` (default) means "not for sale"
    # — free tier is the obvious case but enterprise typically also
    # has a custom-quote price and is hidden from self-serve.
    stripe_price_setting: str = ""
    # Metered price for token-overage billing. Optional.
    stripe_metered_price_setting: str = ""
    # Posted monthly price — what we charge if the Stripe price runs
    # with this plan. Kept in sync manually with the Stripe dashboard;
    # used for the platform admin's MRR/ARR estimate so we don't have
    # to hit the Stripe API on every dashboard render. ``0`` = free /
    # custom-quoted (enterprise).
    monthly_price_cents_usd: int = 0
    # Vietnamese MoMo / bank-transfer price (đồng). Same purpose;
    # zero when the plan isn't offered in VND.
    monthly_price_vnd: int = 0

    def stripe_price_id(self) -> str | None:
        return getattr(settings, self.stripe_price_setting, "") or None if self.stripe_price_setting else None

    def stripe_metered_price_id(self) -> str | None:
        if not self.stripe_metered_price_setting:
            return None
        return getattr(settings, self.stripe_metered_price_setting, "") or None

    def has_feature(self, name: str) -> bool:
        v = self.features.get(name, False)
        # Numeric features (audit retention days) are truthy iff > 0.
        return bool(v)

    def feature_value(self, name: str, default: int | bool = 0) -> int | bool:
        return self.features.get(name, default)

    def is_self_serve(self) -> bool:
        """Plans visible in the upgrade UI. Enterprise hidden — sales-led."""
        return bool(self.stripe_price_id())


PLANS: dict[str, Plan] = {
    PLAN_FREE: Plan(
        code=PLAN_FREE,
        name="Free",
        monthly_llm_tokens=100_000,
        monthly_kb_queries=1_000,
        max_workspaces=1,
        max_members=3,
        features={
            "audit_retention_days": 7,
            "custom_roles": False,
            # SSO + MFA are baseline security controls, available on
            # every tier — they're not paywall levers. Anti-"SSO tax"
            # stance: charging for security punishes customers for
            # doing the right thing.
            "sso": True,
            "mfa_enforce": True,
            "webhook_hmac": False,
            "trace_provider": False,
        },
    ),
    PLAN_STARTER: Plan(
        code=PLAN_STARTER,
        name="Starter",
        monthly_llm_tokens=1_000_000,
        monthly_kb_queries=10_000,
        max_workspaces=3,
        max_members=10,
        features={
            "audit_retention_days": 30,
            "custom_roles": True,
            "sso": True,
            "mfa_enforce": True,
            "webhook_hmac": True,
            "trace_provider": False,
        },
        stripe_price_setting="STRIPE_PRICE_STARTER",
        stripe_metered_price_setting="STRIPE_PRICE_STARTER_METERED",
        monthly_price_cents_usd=1900,        # $19
        monthly_price_vnd=470_000,
    ),
    PLAN_PRO: Plan(
        code=PLAN_PRO,
        name="Pro",
        monthly_llm_tokens=10_000_000,
        monthly_kb_queries=100_000,
        max_workspaces=UNLIMITED,
        max_members=50,
        features={
            "audit_retention_days": 90,
            "custom_roles": True,
            "sso": True,
            "mfa_enforce": True,
            "webhook_hmac": True,
            "trace_provider": True,
        },
        stripe_price_setting="STRIPE_PRICE_PRO",
        stripe_metered_price_setting="STRIPE_PRICE_PRO_METERED",
        monthly_price_cents_usd=9900,        # $99
        monthly_price_vnd=2_500_000,
    ),
    PLAN_ENTERPRISE: Plan(
        code=PLAN_ENTERPRISE,
        name="Enterprise",
        monthly_llm_tokens=UNLIMITED,
        monthly_kb_queries=UNLIMITED,
        max_workspaces=UNLIMITED,
        max_members=UNLIMITED,
        features={
            "audit_retention_days": 365,
            "custom_roles": True,
            "sso": True,
            "mfa_enforce": True,
            "webhook_hmac": True,
            "trace_provider": True,
            "ip_allowlist": True,
            "scim": True,
        },
        # Enterprise is sales-led. Setting these env vars surfaces it
        # in /api/billing/plans for self-serve; leaving them empty
        # keeps it hidden until a deal is signed and price minted.
        stripe_price_setting="STRIPE_PRICE_ENTERPRISE",
        stripe_metered_price_setting="STRIPE_PRICE_ENTERPRISE_METERED",
    ),
}


def get_plan(code: str | None) -> Plan:
    """Resolve a plan code → Plan, falling back to free for unknowns.

    Tolerating unknown codes here means a stale ``organizations.plan``
    value (e.g. an old "team" tier that no longer exists) downgrades
    gracefully to free rather than crashing every quota check.
    """
    if not code:
        return PLANS[PLAN_FREE]
    return PLANS.get(code) or PLANS[PLAN_FREE]


def self_serve_plans() -> list[Plan]:
    """Plans the FE upgrade picker should display."""
    return [p for p in PLANS.values() if p.is_self_serve()]
