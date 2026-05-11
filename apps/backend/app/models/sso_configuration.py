"""SSO configuration per organization — one row per IdP.

SAML and OIDC share the table; provider-specific fields are nullable.
The auth-flow code reads ``provider`` and routes to the right handler.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin

# Provider enum-like values. Stored as String for the same reason
# we use strings everywhere else (additive, no migration to add new).
SSO_PROVIDER_SAML = "saml"
SSO_PROVIDER_OIDC = "oidc"

SSO_PROVIDERS = (SSO_PROVIDER_SAML, SSO_PROVIDER_OIDC)


class SSOConfiguration(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "sso_configurations"
    __table_args__ = (
        UniqueConstraint("organization_id", "provider", name="uq_sso_org_provider"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # ── SAML
    saml_idp_entity_id: Mapped[str | None] = mapped_column(Text)
    saml_idp_sso_url: Mapped[str | None] = mapped_column(Text)
    saml_idp_x509_cert: Mapped[str | None] = mapped_column(Text)
    saml_sp_entity_id: Mapped[str | None] = mapped_column(Text)

    # ── OIDC
    oidc_issuer: Mapped[str | None] = mapped_column(Text)
    oidc_client_id: Mapped[str | None] = mapped_column(String(255))
    # Fernet-encrypted client secret — call ``security.crypto.decrypt_secret``
    # at use time, never store/log plaintext.
    oidc_client_secret_encrypted: Mapped[str | None] = mapped_column(Text)
    oidc_scopes: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        server_default='["openid", "email", "profile"]',
    )

    # ── Common
    default_role: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="editor"
    )
    jit_provisioning: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    # IdP claim → our user field. Empty dict means use OIDC defaults
    # (``email``, ``name``, ``sub``). Populate for non-standard IdPs.
    attribute_mapping: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
