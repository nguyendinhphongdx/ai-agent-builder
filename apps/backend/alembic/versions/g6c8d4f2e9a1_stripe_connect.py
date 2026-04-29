"""users stripe connect account fields

Revision ID: g6c8d4f2e9a1
Revises: f5b9e3a7c1d4
Create Date: 2026-04-29 14:35:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "g6c8d4f2e9a1"
down_revision: Union[str, None] = "f5b9e3a7c1d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Stripe Express Connect account id (e.g. "acct_1OQjK..."). Authors who
    # publish paid templates must complete onboarding to receive payouts.
    op.add_column(
        "users",
        sa.Column("stripe_account_id", sa.String(64), nullable=True),
    )
    # Cached from Stripe's `account.updated` webhook so we don't have to
    # round-trip on every page load. False until the author completes
    # identity verification + bank linking; flips back to false if Stripe
    # later disables the account.
    op.add_column(
        "users",
        sa.Column(
            "stripe_charges_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "stripe_payouts_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    # Unique so we can `ON CONFLICT (stripe_account_id) DO UPDATE` from the
    # webhook handler. Partial — most users will never connect.
    op.execute(
        "CREATE UNIQUE INDEX ux_users_stripe_account "
        "ON users (stripe_account_id) WHERE stripe_account_id IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ux_users_stripe_account")
    op.drop_column("users", "stripe_payouts_enabled")
    op.drop_column("users", "stripe_charges_enabled")
    op.drop_column("users", "stripe_account_id")
