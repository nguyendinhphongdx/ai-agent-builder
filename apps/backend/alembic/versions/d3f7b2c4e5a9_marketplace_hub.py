"""marketplace hub — agent_templates + versions + purchases + agents.template refs

Revision ID: d3f7b2c4e5a9
Revises: c2d5f3e9b6a8
Create Date: 2026-04-29 00:02:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "d3f7b2c4e5a9"
down_revision: Union[str, None] = "c2d5f3e9b6a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── agent_templates ──────────────────────────────────────────────
    op.create_table(
        "agent_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("slug", sa.String(120), nullable=False, unique=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("author_name", sa.String(100), nullable=False),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("cover_image_url", sa.Text(), nullable=True),
        sa.Column("price_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="'USD'"),
        sa.Column("status", sa.String(20), nullable=False, server_default="'draft'"),
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("fork_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rating_avg", sa.Numeric(3, 2), nullable=True),
        sa.Column("rating_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("published_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_templates_user_id", "agent_templates", ["user_id"])
    op.create_index("ix_agent_templates_status", "agent_templates", ["status"])
    op.create_index(
        "ix_agent_templates_browse",
        "agent_templates",
        ["status", "is_featured", "fork_count"],
        postgresql_where=sa.text("status = 'published'"),
    )

    # Postgres FTS on title + description for browse search.
    op.execute(
        """
        ALTER TABLE agent_templates ADD COLUMN search_vector tsvector
        GENERATED ALWAYS AS (
            setweight(to_tsvector('simple', coalesce(title, '')), 'A') ||
            setweight(to_tsvector('simple', coalesce(description, '')), 'B')
        ) STORED
        """
    )
    op.create_index(
        "ix_agent_templates_search",
        "agent_templates",
        ["search_vector"],
        postgresql_using="gin",
    )

    # ── agent_template_versions ──────────────────────────────────────
    op.create_table(
        "agent_template_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.String(20), nullable=False),  # semver
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("changelog", sa.Text(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("template_id", "version", name="uq_template_version"),
    )
    op.create_index("ix_template_versions_template", "agent_template_versions", ["template_id"])
    op.create_index(
        "ix_template_versions_current",
        "agent_template_versions",
        ["template_id"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
    )

    # ── agent_template_purchases ─────────────────────────────────────
    # Created even for free forks so we have a single audit trail.
    op.create_table(
        "agent_template_purchases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("buyer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_template_versions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("price_paid_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="'USD'"),
        sa.Column("status", sa.String(20), nullable=False, server_default="'paid'"),
        sa.Column("stripe_payment_intent_id", sa.String(255), nullable=True),
        sa.Column("purchased_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("refunded_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("ix_purchases_buyer_template", "agent_template_purchases", ["buyer_id", "template_id"])

    # ── agents: forked-from references ───────────────────────────────
    op.add_column(
        "agents",
        sa.Column("template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_templates.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column(
        "agents",
        sa.Column("template_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_template_versions.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_agents_template_id", "agents", ["template_id"])


def downgrade() -> None:
    op.drop_index("ix_agents_template_id", table_name="agents")
    op.drop_column("agents", "template_version_id")
    op.drop_column("agents", "template_id")
    op.drop_index("ix_purchases_buyer_template", table_name="agent_template_purchases")
    op.drop_table("agent_template_purchases")
    op.drop_index("ix_template_versions_current", table_name="agent_template_versions")
    op.drop_index("ix_template_versions_template", table_name="agent_template_versions")
    op.drop_table("agent_template_versions")
    op.drop_index("ix_agent_templates_search", table_name="agent_templates")
    op.drop_index("ix_agent_templates_browse", table_name="agent_templates")
    op.drop_index("ix_agent_templates_status", table_name="agent_templates")
    op.drop_index("ix_agent_templates_user_id", table_name="agent_templates")
    op.drop_table("agent_templates")
