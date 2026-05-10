"""organizations + workspaces + members + invitations

Phase 1.1 step 1 of the multi-tenancy rollout — adds the four new
tables only. No existing tables are touched, no data migration runs
yet, so this is fully reversible: ``alembic downgrade -1`` drops the
four tables and the schema is back to single-tenant.

Subsequent steps (in later migrations):
  - Step 2: add nullable ``workspace_id`` columns to every resource
    table (agents, tools, knowledge_bases, …).
  - Step 3: backfill — create one personal Organization + Workspace
    per existing user, populate ``workspace_id`` everywhere, set the
    user as the workspace ``owner``.
  - Step 4: ``ALTER COLUMN workspace_id SET NOT NULL`` once backfill
    is verified clean.

Splitting it this way keeps each migration small enough to roll back
without dragging an org's data with it.

Revision ID: m2c4d8e1f3a5
Revises: l1b3c9e7d5f2
Create Date: 2026-05-10 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "m2c4d8e1f3a5"
down_revision: Union[str, None] = "l1b3c9e7d5f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── organizations ─────────────────────────────────────────────────
    op.create_table(
        "organizations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("billing_email", sa.String(length=255), nullable=True),
        sa.Column(
            "plan",
            sa.String(length=20),
            nullable=False,
            server_default="free",
        ),
        sa.Column(
            "settings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_organizations_slug"),
    )
    op.create_index(
        op.f("ix_organizations_slug"), "organizations", ["slug"], unique=True
    )

    # ── workspaces ────────────────────────────────────────────────────
    op.create_table(
        "workspaces",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column(
            "is_personal",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "settings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
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
        sa.UniqueConstraint(
            "organization_id", "slug", name="uq_workspace_org_slug"
        ),
    )
    op.create_index(
        op.f("ix_workspaces_organization_id"),
        "workspaces",
        ["organization_id"],
        unique=False,
    )

    # ── workspace_members ─────────────────────────────────────────────
    op.create_table(
        "workspace_members",
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("invited_by", sa.UUID(), nullable=True),
        sa.Column(
            "joined_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["invited_by"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("workspace_id", "user_id"),
    )
    # Lookup-by-user index: every page load needs "what workspaces is
    # this user in?" — without this it's a full scan of the join table.
    op.create_index(
        op.f("ix_workspace_members_user_id"),
        "workspace_members",
        ["user_id"],
        unique=False,
    )

    # ── workspace_invitations ─────────────────────────────────────────
    op.create_table(
        "workspace_invitations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column(
            "expires_at", sa.TIMESTAMP(timezone=True), nullable=False
        ),
        sa.Column("accepted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("invited_by", sa.UUID(), nullable=True),
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
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["invited_by"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token", name="uq_workspace_invitations_token"),
    )
    op.create_index(
        op.f("ix_workspace_invitations_workspace_id"),
        "workspace_invitations",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_workspace_invitations_email"),
        "workspace_invitations",
        ["email"],
        unique=False,
    )
    op.create_index(
        op.f("ix_workspace_invitations_token"),
        "workspace_invitations",
        ["token"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_workspace_invitations_token"), table_name="workspace_invitations"
    )
    op.drop_index(
        op.f("ix_workspace_invitations_email"), table_name="workspace_invitations"
    )
    op.drop_index(
        op.f("ix_workspace_invitations_workspace_id"),
        table_name="workspace_invitations",
    )
    op.drop_table("workspace_invitations")

    op.drop_index(
        op.f("ix_workspace_members_user_id"), table_name="workspace_members"
    )
    op.drop_table("workspace_members")

    op.drop_index(
        op.f("ix_workspaces_organization_id"), table_name="workspaces"
    )
    op.drop_table("workspaces")

    op.drop_index(op.f("ix_organizations_slug"), table_name="organizations")
    op.drop_table("organizations")
