"""users.momo_* — per-author MoMo merchant credentials

Revision ID: k0a2b8d6f4e1
Revises: j9f1a7c5e2d0
Create Date: 2026-04-29 17:10:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "k0a2b8d6f4e1"
down_revision: Union[str, None] = "j9f1a7c5e2d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Per-author MoMo Business merchant credentials. Authors register
    # with MoMo themselves out-of-band, then paste the resulting trio
    # into Settings → Author Payouts. Encrypted at rest with the same
    # Fernet key that protects ai_credentials. NULL = author hasn't
    # connected; checkout falls back to platform-collects.
    op.add_column(
        "users",
        sa.Column("momo_partner_code", sa.String(64), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("momo_access_key_enc", sa.Text(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("momo_secret_key_enc", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "momo_secret_key_enc")
    op.drop_column("users", "momo_access_key_enc")
    op.drop_column("users", "momo_partner_code")
