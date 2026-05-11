"""audit_logs table (Phase 1.4 — tenant-scoped audit trail)

Append-only ledger of every critical action across the platform.
Distinct from ``admin_actions``: that one is staff-only (template
moderation, refunds, grant-role). ``audit_logs`` records all
tenant-visible events — workspace membership changes, MFA on/off,
SSO config edits, SCIM token mints, etc. — so org admins can see
who did what in their tenant without giving them platform-admin.

Schema deliberately wide-and-loose:
  - ``action`` is a dotted string ("workspace.member.invite",
    "mfa.disable") — adding a new event type is a string change,
    not a migration.
  - ``resource_type`` + ``resource_id`` are nullable so events
    without a single target (login, logout) still fit.
  - ``metadata`` JSONB carries event-specific detail (the role
    granted, the role demoted from, etc.). No schema in the DB —
    each producer decides what's useful.

Indexed for the two common query shapes:
  1. "Show me everything in org X, newest first" (admin UI)
  2. "Who touched resource Y?" (right-rail in resource detail)

Revision ID: w2m5n8i1j4k6
Revises: v1l4m7h0i3j5
Create Date: 2026-05-11 07:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "w2m5n8i1j4k6"
down_revision: Union[str, None] = "v1l4m7h0i3j5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        # NULL for platform-level events that don't belong to any org
        # (e.g. failed login attempts before user is resolved).
        sa.Column("organization_id", sa.UUID(), nullable=True),
        sa.Column("workspace_id", sa.UUID(), nullable=True),
        # NULL = system action. Most rows carry a user; cron triggers
        # and SCIM-driven changes don't.
        sa.Column("actor_user_id", sa.UUID(), nullable=True),
        # user | api_token | scim | system | sso. Use the enum-as-string
        # convention so future actor types add without migration.
        sa.Column("actor_type", sa.String(length=20), nullable=False),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=True),
        sa.Column("resource_id", sa.String(length=64), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
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
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # Admin/audit "newest first per org" — the primary list query.
    op.create_index(
        op.f("ix_audit_logs_org_created"),
        "audit_logs",
        ["organization_id", sa.text("created_at DESC")],
        unique=False,
    )
    # Workspace-scoped variant (workspace admins viewing their own
    # workspace's activity).
    op.create_index(
        op.f("ix_audit_logs_workspace_created"),
        "audit_logs",
        ["workspace_id", sa.text("created_at DESC")],
        unique=False,
    )
    # "Who touched this resource?" — right-rail history.
    op.create_index(
        op.f("ix_audit_logs_resource"),
        "audit_logs",
        ["resource_type", "resource_id", sa.text("created_at DESC")],
        unique=False,
    )
    # Compliance queries — find all actions of a given type platform-wide.
    op.create_index(
        op.f("ix_audit_logs_action_created"),
        "audit_logs",
        ["action", sa.text("created_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_action_created"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_resource"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_workspace_created"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_org_created"), table_name="audit_logs")
    op.drop_table("audit_logs")
