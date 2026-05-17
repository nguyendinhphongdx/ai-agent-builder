"""Organization — top-level tenant in the multi-tenancy hierarchy.

Layout: ``Organization > Workspace(s) > resources``. Every workspace
belongs to exactly one organization; resources (agents, KBs, …) live
inside a workspace and inherit the organization's billing/plan.

Personal accounts get a single auto-created Organization with a single
``is_personal=true`` Workspace at signup, so single-user usage flows
through the same code paths as multi-tenant teams.
"""
from __future__ import annotations

from sqlalchemy import Boolean, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.platform.db.base import Base, TimestampMixin, UUIDMixin

# Plan tier — kept as String column (not Enum) to match the project's
# convention and so we can roll out new plans via seed data without a
# schema migration. Enforced at the service layer.
ORG_PLAN_FREE = "free"
ORG_PLAN_STARTER = "starter"
ORG_PLAN_PRO = "pro"
ORG_PLAN_ENTERPRISE = "enterprise"

# Slug + name used by ``seed_root_org`` when bootstrapping the platform
# owner's org. The slug is for routing / display; the AUTH source of
# truth is the ``is_system`` column on the row (see below) — never check
# slug for permission decisions.
SYSTEM_ORG_SLUG = "system"
SYSTEM_ORG_NAME = "AgentForge Platform"


class Organization(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "organizations"
    __table_args__ = (
        # DB-enforced singleton: at most one row may have ``is_system=true``.
        # The partial WHERE clause keeps the rest of the table free to share
        # the default ``false`` value. Source of truth for platform-admin auth.
        Index(
            "ux_organizations_system_singleton",
            "is_system",
            unique=True,
            postgresql_where=text("is_system = true"),
        ),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # URL-safe identifier (lowercase, hyphenated). Used in subdomain or
    # path routing for SSO endpoints, custom branding lookups, etc.
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    # Where invoices/receipts get sent. Falls back to the owner's email
    # if not set explicitly.
    billing_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Plan tier — drives quota + feature gating. Default 'free' for any
    # personal-account org auto-created at signup.
    plan: Mapped[str] = mapped_column(
        String(20), default=ORG_PLAN_FREE, server_default=ORG_PLAN_FREE, nullable=False
    )
    # White-label / branding settings (logo URL, primary color, …).
    # Free-form JSON so the UI can evolve without migrations.
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}", nullable=False)
    # Platform-owner marker. Exactly one row may have ``True`` (partial
    # unique index in migration). This is the SOURCE OF TRUTH for
    # platform-admin authorization — see ``require_platform_admin``.
    is_system: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )

    workspaces: Mapped[list["Workspace"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
