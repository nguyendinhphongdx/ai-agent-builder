"""users.default_workspace_id

Lets the app remember which workspace each user landed in last so
login redirects to a useful page instead of forcing a chooser. Set
on signup by ``ensure_personal_workspace`` (auto-points at the user's
personal workspace), then updated by the workspace switcher.

Nullable: existing rows have no workspace yet (this migration runs
before backfill). Service layer treats NULL as "user has no
workspaces — kick them through onboarding".

Revision ID: n3d5e9f2a4b6
Revises: m2c4d8e1f3a5
Create Date: 2026-05-11 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "n3d5e9f2a4b6"
down_revision: Union[str, None] = "m2c4d8e1f3a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("default_workspace_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_users_default_workspace_id",
        "users",
        "workspaces",
        ["default_workspace_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_users_default_workspace_id"),
        "users",
        ["default_workspace_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_users_default_workspace_id"), table_name="users")
    op.drop_constraint("fk_users_default_workspace_id", "users", type_="foreignkey")
    op.drop_column("users", "default_workspace_id")
