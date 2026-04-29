"""payment provider generalization (Stripe + MoMo)

Revision ID: h7d9e5a3b2c8
Revises: g6c8d4f2e9a1
Create Date: 2026-04-29 15:05:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "h7d9e5a3b2c8"
down_revision: Union[str, None] = "g6c8d4f2e9a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


VALID_PROVIDERS = ("stripe", "momo")


def upgrade() -> None:
    # Add `provider` first with a default so the existing rows backfill to
    # 'stripe' (the only paid path before this migration).
    op.add_column(
        "agent_template_purchases",
        sa.Column("provider", sa.String(20), nullable=False, server_default="stripe"),
    )
    op.create_check_constraint(
        "ck_agent_template_purchases_provider",
        "agent_template_purchases",
        f"provider IN {VALID_PROVIDERS}",
    )

    # Rename the Stripe-specific id column to a provider-agnostic name.
    # Existing values keep their meaning under the new name.
    op.alter_column(
        "agent_template_purchases",
        "stripe_payment_intent_id",
        new_column_name="provider_transaction_id",
        existing_type=sa.String(255),
        existing_nullable=True,
    )

    # Webhook handlers look up the Purchase by (provider, txn_id). Index
    # the pair so that lookup stays cheap as volume grows.
    op.create_index(
        "ix_purchases_provider_txn",
        "agent_template_purchases",
        ["provider", "provider_transaction_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_purchases_provider_txn", table_name="agent_template_purchases")
    op.alter_column(
        "agent_template_purchases",
        "provider_transaction_id",
        new_column_name="stripe_payment_intent_id",
        existing_type=sa.String(255),
        existing_nullable=True,
    )
    op.drop_constraint(
        "ck_agent_template_purchases_provider",
        "agent_template_purchases",
        type_="check",
    )
    op.drop_column("agent_template_purchases", "provider")
