"""agent_template_reviews — buyers rate templates they've forked

Revision ID: e4a8c1f5d2b6
Revises: d3f7b2c4e5a9
Create Date: 2026-04-29 00:03:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "e4a8c1f5d2b6"
down_revision: Union[str, None] = "d3f7b2c4e5a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_template_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),  # 1..5
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        # One review per (user, template) — editing replaces the existing row.
        sa.UniqueConstraint("template_id", "user_id", name="uq_review_per_user_template"),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_rating_range"),
    )
    op.create_index("ix_reviews_template", "agent_template_reviews", ["template_id"])


def downgrade() -> None:
    op.drop_index("ix_reviews_template", table_name="agent_template_reviews")
    op.drop_table("agent_template_reviews")
