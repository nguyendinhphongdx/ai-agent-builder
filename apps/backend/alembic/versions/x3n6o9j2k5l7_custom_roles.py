"""custom_roles table (Phase 1.5 Block 3 — org-defined permission sets)

Lets org admins define roles beyond the four built-ins. A custom
role's ``slug`` lives in ``workspace_members.role`` exactly like
a built-in role string — the permission resolver checks built-ins
first, then falls back to this table.

Revision ID: x3n6o9j2k5l7
Revises: w2m5n8i1j4k6
Create Date: 2026-05-11 08:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "x3n6o9j2k5l7"
down_revision: Union[str, None] = "w2m5n8i1j4k6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "custom_roles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        # Array of permission strings (from app.platform.permissions.catalogue).
        # Validated at the service layer — unknown strings are rejected
        # before insert.
        sa.Column(
            "permissions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "slug", name="uq_custom_roles_org_slug"),
    )
    op.create_index(
        op.f("ix_custom_roles_organization_id"),
        "custom_roles",
        ["organization_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_custom_roles_organization_id"), table_name="custom_roles"
    )
    op.drop_table("custom_roles")
