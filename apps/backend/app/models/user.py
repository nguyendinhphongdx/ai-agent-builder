from datetime import datetime

from sqlalchemy import TIMESTAMP, Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class User(Base, UUIDMixin, TimestampMixin):
    """Model người dùng - quản lý tài khoản, xác thực và quan hệ với các tài nguyên."""
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    # Nullable: OAuth-only users never set a password.
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(String(512))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    # Platform-level role hierarchy (orthogonal to any future tenant role):
    # user < moderator < support < admin. See `app.auth.permissions`.
    role: Mapped[str] = mapped_column(String(20), default="user", server_default="user", nullable=False)
    # Bumped when all refresh sessions must be invalidated (eg. password reset).
    # Refresh JWTs carry `ver`; mismatch → reject.
    token_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    # ── Stripe Connect (Hub paid template payouts) ──────────────────────
    # Express account id, populated when the author starts onboarding.
    # `charges_enabled` flips true after Stripe finishes identity verification
    # + bank linking; we mirror it from the `account.updated` webhook so the
    # publish-paid gate doesn't round-trip the Stripe API.
    stripe_account_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    stripe_charges_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    stripe_payouts_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )

    # Quan hệ 1-N: user sở hữu nhiều agents, tools, KBs, conversations, API keys
    agents: Mapped[list["Agent"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    tools: Mapped[list["Tool"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    knowledge_bases: Mapped[list["KnowledgeBase"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    ai_credentials: Mapped[list["AICredential"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    personal_access_tokens: Mapped[list["PersonalAccessToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
