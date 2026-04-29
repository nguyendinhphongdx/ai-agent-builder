"""AuthToken — one-shot email-verification / password-reset tokens."""

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin

# Purpose values persisted in auth_tokens.purpose
PURPOSE_EMAIL_VERIFICATION = "email_verification"
PURPOSE_PASSWORD_RESET = "password_reset"
# Self-change-email — code emailed to the *new* address; the requested
# address is staged on `users.pending_email` between request and confirm.
PURPOSE_EMAIL_CHANGE = "email_change"


class AuthToken(Base, UUIDMixin):
    """One-shot token for email verification or password reset.

    Plaintext token values are **never** stored. We persist ``sha256(token)``
    in ``token_hash`` and compare the hash when the user redeems the link.
    Once a token is redeemed the row stays but ``used_at`` is stamped so the
    same URL cannot be reused.
    """

    __tablename__ = "auth_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )

    __table_args__ = (
        Index("idx_auth_tokens_user_purpose", "user_id", "purpose"),
    )
