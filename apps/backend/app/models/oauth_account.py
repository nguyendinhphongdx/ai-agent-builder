"""OAuthAccount — links an external provider identity to an internal user."""

import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin

# Supported provider identifiers
PROVIDER_GITHUB = "github"
PROVIDER_GOOGLE = "google"


class OAuthAccount(Base, UUIDMixin, TimestampMixin):
    """A verified identity on a third-party provider bound to a local user.

    (provider, provider_user_id) is the uniqueness key — the provider's ID
    is stable even if the user changes their email on the provider side.
    """

    __tablename__ = "oauth_accounts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_email: Mapped[str] = mapped_column(String(255), nullable=False)
    # Tokens are optional — only stored if we plan to call provider APIs.
    access_token: Mapped[str | None] = mapped_column(Text)
    refresh_token: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_oauth_provider_user"),
    )
