"""users.pending_email — staging field for self-change email flow

Revision ID: j9f1a7c5e2d0
Revises: i8e0f6b4d3c9
Create Date: 2026-04-29 16:55:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "j9f1a7c5e2d0"
down_revision: Union[str, None] = "i8e0f6b4d3c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Holds the *requested new* email between `POST /me/email` (we mail a
    # verification code to this address) and `POST /me/email/confirm`
    # (we redeem the code + swap users.email = pending_email).
    # NULL most of the time — the column only carries data for the brief
    # window between request and confirm.
    op.add_column(
        "users",
        sa.Column("pending_email", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "pending_email")
