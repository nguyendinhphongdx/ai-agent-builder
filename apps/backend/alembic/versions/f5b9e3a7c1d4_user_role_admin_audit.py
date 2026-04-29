"""users.role + admin_actions audit log

Revision ID: f5b9e3a7c1d4
Revises: e4a8c1f5d2b6
Create Date: 2026-04-29 00:04:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "f5b9e3a7c1d4"
down_revision: Union[str, None] = "e4a8c1f5d2b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


VALID_ROLES = ("user", "moderator", "support", "admin")


def upgrade() -> None:
    # ── users.role — platform-level role hierarchy ───────────────────
    op.add_column(
        "users",
        sa.Column("role", sa.String(20), nullable=False, server_default="user"),
    )
    op.create_check_constraint(
        "ck_users_role",
        "users",
        f"role IN {VALID_ROLES}",
    )
    # Partial index — only ~5-10 staff among many users; full-table index
    # would be wasted. WHERE role != 'user' keeps the index tiny.
    op.execute(
        "CREATE INDEX ix_users_role_staff ON users (role) WHERE role != 'user'"
    )

    # ── admin_actions — audit log of staff actions ───────────────────
    op.create_table(
        "admin_actions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "actor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Free-text so we can add new actions without schema changes.
        # Examples: 'template.feature', 'template.suspend', 'user.ban',
        # 'user.grant_role', 'purchase.refund'.
        sa.Column("action", sa.String(50), nullable=False),
        # Loose target — can point at template id, user id, purchase id, etc.
        sa.Column("target_type", sa.String(50), nullable=True),
        sa.Column("target_id", sa.String(64), nullable=True),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_admin_actions_actor", "admin_actions", ["actor_user_id"])
    op.create_index(
        "ix_admin_actions_target", "admin_actions", ["target_type", "target_id"]
    )
    op.create_index("ix_admin_actions_created", "admin_actions", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_admin_actions_created", table_name="admin_actions")
    op.drop_index("ix_admin_actions_target", table_name="admin_actions")
    op.drop_index("ix_admin_actions_actor", table_name="admin_actions")
    op.drop_table("admin_actions")
    op.execute("DROP INDEX IF EXISTS ix_users_role_staff")
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.drop_column("users", "role")
