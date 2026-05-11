"""Tenant-scoped audit log row.

Distinct from :class:`AdminAction` — that one is platform-staff
operations (template moderation, refunds, grant-role). This is the
broader audit trail visible to org admins.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin

# Canonical actor types — see app/audit/service.py for the constants
# used when writing. Loose strings on the column so future kinds
# (e.g. ``service_account``) add without migration.
ACTOR_USER = "user"
ACTOR_API_TOKEN = "api_token"
ACTOR_SCIM = "scim"
ACTOR_SSO = "sso"
ACTOR_SYSTEM = "system"


class AuditLog(Base, UUIDMixin):
    __tablename__ = "audit_logs"

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
    )
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # Dotted event name. Convention: ``<domain>.<verb>`` or
    # ``<domain>.<noun>.<verb>``. Examples:
    #   "auth.login.success", "auth.login.failed", "auth.logout"
    #   "workspace.member.invite", "workspace.member.role_change"
    #   "mfa.totp.enable", "mfa.totp.disable", "mfa.backup_codes.regenerate"
    #   "sso.config.update", "scim.token.mint", "scim.token.revoke"
    #   "ip_rule.create", "ip_rule.delete"
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(64))
    resource_id: Mapped[str | None] = mapped_column(String(64))
    ip_address: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(Text)
    # SQLAlchemy reserves ``metadata`` on Base — alias the attribute
    # ``data`` to map onto the ``metadata`` column.
    data: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default="now()", nullable=False
    )
