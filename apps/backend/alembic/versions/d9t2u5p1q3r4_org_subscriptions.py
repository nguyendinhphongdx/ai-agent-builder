"""org_subscriptions table (Phase 2.3 Block 1)

One row per organization tracking its current Stripe subscription
state. Plan tier still lives on ``organizations.plan`` for fast
lookup paths (request-time quota check needs no extra join) — this
table carries the *billing* fields: Stripe identifiers, period
boundaries, payment status, scheduled downgrade flag.

Why a separate table:
  - Organizations existed before paid plans; not every org will ever
    have a subscription row (legacy free tier needs none).
  - Stripe ids are PII-adjacent and rotate per environment — keeping
    them isolated makes test-vs-prod data hygiene clearer.
  - History-ready: today we keep one active row per org via the
    unique constraint; future "subscription audit log" can layer on.

Revision ID: d9t2u5p1q3r4
Revises: c8s1t4o7p0q2
Create Date: 2026-05-11 14:30:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "d9t2u5p1q3r4"
down_revision: Union[str, None] = "c8s1t4o7p0q2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "org_subscriptions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        # Mirrors organizations.plan, but is the *billed* plan rather
        # than the *effective* plan. Diverges briefly while a downgrade
        # is queued for end-of-period.
        sa.Column("plan_code", sa.String(length=32), nullable=False),
        # Stripe subscription status — active | trialing | past_due |
        # incomplete | canceled | unpaid. Used by quota guards to
        # decide whether to fall back to free-tier limits.
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True),
        # Stripe sub-item id for the metered token-overage price.
        # Stored once at subscription creation so the usage reporter
        # doesn't have to refetch the subscription each tick.
        sa.Column("stripe_metered_item_id", sa.String(length=255), nullable=True),
        sa.Column("current_period_start", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.TIMESTAMP(timezone=True), nullable=True),
        # Set by Stripe Billing Portal "cancel at period end" or our
        # own downgrade endpoint. Quota stays at current plan until
        # the period flips; then webhook drops it to free.
        sa.Column(
            "cancel_at_period_end",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        # Cursor for the metered-usage reporter: id of the last
        # usage_events row already shipped to Stripe. The reporter
        # ships rows with id > this cursor each tick.
        sa.Column("last_reported_event_id", sa.UUID(), nullable=True),
        sa.Column("last_reported_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "extra",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", name="uq_org_subscriptions_org"),
        sa.UniqueConstraint(
            "stripe_subscription_id", name="uq_org_subscriptions_stripe_sub"
        ),
    )
    # Webhook handlers look up by Stripe ids — fast path needs an index
    # on customer_id (subscription_id is already covered by the unique).
    op.create_index(
        "ix_org_subscriptions_stripe_customer",
        "org_subscriptions",
        ["stripe_customer_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_org_subscriptions_stripe_customer", table_name="org_subscriptions")
    op.drop_table("org_subscriptions")
