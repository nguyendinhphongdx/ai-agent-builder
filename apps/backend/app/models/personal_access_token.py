"""Personal access token — long-lived credential for external API access.

Issued by users to grant 3rd-party apps/scripts ability to call ``/api/external/*``
endpoints on their behalf. Plaintext value is shown ONCE at creation time and
never again — only the SHA-256 hash is persisted.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDMixin


class PersonalAccessToken(Base, UUIDMixin):
    """User-owned API token with scope-based authorization."""

    __tablename__ = "personal_access_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Display label so user can identify what each token is for in the UI.
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # SHA-256 hex of the plaintext token. Unique so we can lookup by hash.
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)

    # First N chars of the plaintext (e.g. "afpt_a1b2c3") — non-secret, helps
    # users distinguish tokens in the list.
    key_prefix: Mapped[str] = mapped_column(String(20), nullable=False)

    # Scopes granted to this token. Coarse-grained: "agents:chat", "agents:read",
    # "conversations:read", "conversations:write", "workflows:execute".
    scopes: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    last_used_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    # Optional hard expiry. Null = lives until revoked.
    expires_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    # Soft revoke — token rejected from this point forward, row kept for audit.
    revoked_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default="now()", nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="personal_access_tokens")
