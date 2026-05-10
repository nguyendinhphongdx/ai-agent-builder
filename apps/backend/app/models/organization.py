"""Organization — top-level tenant in the multi-tenancy hierarchy.

Layout: ``Organization > Workspace(s) > resources``. Every workspace
belongs to exactly one organization; resources (agents, KBs, …) live
inside a workspace and inherit the organization's billing/plan.

Personal accounts get a single auto-created Organization with a single
``is_personal=true`` Workspace at signup, so single-user usage flows
through the same code paths as multi-tenant teams.
"""
from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


# Plan tier — kept as String column (not Enum) to match the project's
# convention and so we can roll out new plans via seed data without a
# schema migration. Enforced at the service layer.
ORG_PLAN_FREE = "free"
ORG_PLAN_STARTER = "starter"
ORG_PLAN_PRO = "pro"
ORG_PLAN_ENTERPRISE = "enterprise"


class Organization(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "organizations"

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

    workspaces: Mapped[list["Workspace"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
