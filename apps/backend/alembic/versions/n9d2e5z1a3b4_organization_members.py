"""organization_members + users.default_organization_id

Shifts identity to org-first multi-tenancy: users join organizations
directly via ``organization_members`` (role: viewer/editor/admin/owner)
instead of only at the workspace tier. ``workspace_members`` stays
in place — its role is now per-project on top of the org role
(ceiling/floor rule documented in
``app.platform.permissions.roles``).

Data migration: derives ``organization_members`` from existing
``workspace_members`` × ``workspaces.organization_id`` pairs. Each
user is granted the MAX of their workspace roles in that org —
prevents accidental demotion for users who were already admins of a
project. Existing ``users.default_workspace_id`` is used to seed
``default_organization_id``.

Revision ID: n9d2e5z1a3b4
Revises: m8c1d4y0z2a3
Create Date: 2026-05-13 09:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "n9d2e5z1a3b4"
down_revision: Union[str, None] = "m8c1d4y0z2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── 1. organization_members table ──────────────────────────────
    op.create_table(
        "organization_members",
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column(
            "invited_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "joined_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
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
        sa.PrimaryKeyConstraint(
            "organization_id", "user_id", name="pk_organization_members"
        ),
    )
    op.create_index(
        "ix_org_members_user", "organization_members", ["user_id"]
    )

    # ─── 2. users.default_organization_id ───────────────────────────
    op.add_column(
        "users",
        sa.Column(
            "default_organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_users_default_organization_id",
        "users",
        ["default_organization_id"],
    )

    # ─── 3. Backfill organization_members from workspace_members ─────
    # MAX-rank wins per (org, user) pair so a user who's owner of one
    # project + editor of another lands as org-level owner.
    op.execute(
        """
        INSERT INTO organization_members
            (organization_id, user_id, role, joined_at, created_at, updated_at)
        SELECT
            w.organization_id,
            wm.user_id,
            CASE MAX(
                CASE wm.role
                    WHEN 'owner'  THEN 4
                    WHEN 'admin'  THEN 3
                    WHEN 'editor' THEN 2
                    WHEN 'viewer' THEN 1
                    ELSE 0
                END
            )
                WHEN 4 THEN 'owner'
                WHEN 3 THEN 'admin'
                WHEN 2 THEN 'editor'
                WHEN 1 THEN 'viewer'
                ELSE 'editor'
            END,
            MIN(wm.joined_at),
            MIN(wm.joined_at),
            now()
        FROM workspace_members wm
        JOIN workspaces w ON w.id = wm.workspace_id
        GROUP BY w.organization_id, wm.user_id
        ON CONFLICT (organization_id, user_id) DO NOTHING;
        """
    )

    # ─── 4. Backfill users.default_organization_id ───────────────────
    op.execute(
        """
        UPDATE users u
        SET default_organization_id = w.organization_id
        FROM workspaces w
        WHERE u.default_workspace_id = w.id
          AND u.default_organization_id IS NULL;
        """
    )


def downgrade() -> None:
    op.drop_index("ix_users_default_organization_id", table_name="users")
    op.drop_column("users", "default_organization_id")
    op.drop_index("ix_org_members_user", table_name="organization_members")
    op.drop_table("organization_members")
