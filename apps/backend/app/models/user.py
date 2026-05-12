import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.platform.db.base import Base, TimestampMixin, UUIDMixin


class User(Base, UUIDMixin, TimestampMixin):
    """Model người dùng - quản lý tài khoản, xác thực và quan hệ với các tài nguyên."""
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    # Nullable: OAuth-only users never set a password.
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Holds the *requested new* email during a self-change-email flow.
    # NULL outside that brief request → confirm window. See auth/router
    # `change_email` + `confirm_email_change`.
    pending_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(String(512))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    # Platform-level role hierarchy (orthogonal to any future tenant role):
    # user < moderator < support < admin. See `app.modules.identity.auth.permissions`.
    role: Mapped[str] = mapped_column(String(20), default="user", server_default="user", nullable=False)
    # Bumped when all refresh sessions must be invalidated (eg. password reset).
    # Refresh JWTs carry `ver`; mismatch → reject.
    token_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    # ── Multi-tenancy ──────────────────────────────────────────────────
    # Where the user lands when they open the app — auto-pointed at
    # their personal workspace at signup, then updated to the last
    # workspace they were viewing. NULL only between user creation and
    # the first ``ensure_personal_workspace`` call (and for legacy rows
    # Every user gets a personal workspace at signup; backfill phase A
    # heals legacy rows. Kept NULLABLE on purpose: ``ON DELETE SET NULL``
    # would otherwise conflict with NOT NULL if the pointed-to workspace
    # is deleted. NULL is the brief recovery state that the auth dep
    # heals on the next request via ``ensure_personal_workspace``.
    default_workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── MFA ───────────────────────────────────────────────────────────
    # Fernet-encrypted TOTP secret (base32 plaintext). NULL = TOTP not
    # enrolled. Use ``security.crypto.decrypt_secret`` at verify time;
    # never persist or log plaintext.
    totp_secret_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    # JSONB array of SHA-256-hashed single-use backup codes. A consumed
    # code is removed from the array on use, so the array length doubles
    # as "remaining codes" for the UI.
    mfa_backup_codes: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    # Convenience flag — true iff any factor is set up. Lets login flow
    # check a single bool instead of inspecting multiple columns.
    mfa_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

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

    # ── MoMo Business — per-author merchant credentials ─────────────────
    # Authors register with MoMo Business out-of-band (Vietnamese business
    # registration required) and paste the resulting trio into Settings.
    # NULL = not connected; VND checkout falls back to platform-collects
    # using settings.MOMO_*. Secret values encrypted via app.platform.security.crypto.
    momo_partner_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    momo_access_key_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    momo_secret_key_enc: Mapped[str | None] = mapped_column(Text, nullable=True)

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

    # Pointer at the user's home workspace (no back_populates — Workspace
    # has many things pointing at it; this is just a UX shortcut, not a
    # navigation edge in the workspace graph).
    default_workspace: Mapped["Workspace | None"] = relationship(
        foreign_keys=[default_workspace_id], lazy="joined"
    )
