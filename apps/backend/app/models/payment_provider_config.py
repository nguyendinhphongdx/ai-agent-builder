"""Platform-level payment-provider configuration.

One row per provider (Stripe, MoMo, VNPay, …). Holds secrets +
non-secret config behind one toggle. Lets a platform admin enable /
disable / swap-test-live a gateway from the admin UI without touching
.env or redeploying.

Secrets live in ``encrypted_secrets`` (Fernet-encrypted JSON keyed by
secret name). The ``config`` JSONB column holds display-safe knobs
(public price ids, fee bps, redirect URL templates, …).

Bootstrap: ``app.platform.cli.seed_payment_providers`` syncs the
seven existing env vars (STRIPE_*, MOMO_*) into rows on first run.
After that the env vars are no longer read — DB is source of truth.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, TIMESTAMP, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db.base import Base, TimestampMixin

# Canonical provider names — match SubscriptionProvider.name +
# PaymentProvider.name. New providers add a constant here so callers
# get a typo-proof handle.
PROVIDER_STRIPE = "stripe"
PROVIDER_MOMO = "momo"


class PaymentProviderConfig(Base, TimestampMixin):
    """One row per gateway. Code is the PK so look-ups are O(1) by name."""

    __tablename__ = "payment_provider_configs"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    # Free / paid / both — informs the FE picker grouping.
    kind: Mapped[str] = mapped_column(
        String(16), nullable=False, default="both", server_default="both"
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    is_test_mode: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    # Fernet-encrypted JSON, e.g. {"secret_key":"...", "webhook_secret":"..."}.
    # Never returned to the FE — admin sees masked previews via service.
    encrypted_secrets: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # Non-secret config visible in the admin UI.
    # e.g. {"price_starter":"price_xxx","platform_fee_bps":1000}.
    config: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=100, server_default="100"
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Last "Test connection" result for ops visibility.
    last_tested_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    last_test_result: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Audit — who touched it last (system org admin).
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
