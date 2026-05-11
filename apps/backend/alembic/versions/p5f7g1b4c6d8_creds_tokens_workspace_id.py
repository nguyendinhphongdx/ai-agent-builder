"""ai_credentials + personal_access_tokens workspace_id (Phase 1.1 step 2 — group A)

Mirrors the agents proof-of-pattern from o4e6f0a3b5c7. Nullable through
the transition; backfill stamps these from each row's ``user_id`` →
that user's personal workspace before the lock migration in step 4
flips the column to NOT NULL.

Revision ID: p5f7g1b4c6d8
Revises: o4e6f0a3b5c7
Create Date: 2026-05-11 01:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "p5f7g1b4c6d8"
down_revision: Union[str, None] = "o4e6f0a3b5c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ai_credentials
    op.add_column(
        "ai_credentials",
        sa.Column("workspace_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_ai_credentials_workspace_id",
        "ai_credentials",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        op.f("ix_ai_credentials_workspace_id"),
        "ai_credentials",
        ["workspace_id"],
        unique=False,
    )

    # personal_access_tokens
    op.add_column(
        "personal_access_tokens",
        sa.Column("workspace_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_personal_access_tokens_workspace_id",
        "personal_access_tokens",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        op.f("ix_personal_access_tokens_workspace_id"),
        "personal_access_tokens",
        ["workspace_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_personal_access_tokens_workspace_id"),
        table_name="personal_access_tokens",
    )
    op.drop_constraint(
        "fk_personal_access_tokens_workspace_id",
        "personal_access_tokens",
        type_="foreignkey",
    )
    op.drop_column("personal_access_tokens", "workspace_id")

    op.drop_index(
        op.f("ix_ai_credentials_workspace_id"),
        table_name="ai_credentials",
    )
    op.drop_constraint(
        "fk_ai_credentials_workspace_id",
        "ai_credentials",
        type_="foreignkey",
    )
    op.drop_column("ai_credentials", "workspace_id")
