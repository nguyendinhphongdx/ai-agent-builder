"""message_annotations table (P3.7)

Per-message thumbs up/down + optional free-text feedback. Drives
the quality dashboard + future fine-tuning dataset export.

Why a separate table (vs. fields on messages):
  - One user can annotate a message exactly once (idempotent via
    unique constraint on (message_id, user_id)).
  - Annotations are mutable independently of message content —
    users can revise a rating without rewriting history.
  - Aggregation queries are cheap with a focused table + index.

Revision ID: j5z8a1v7w9x0
Revises: i4y7z0u6v8w9
Create Date: 2026-05-12 10:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "j5z8a1v7w9x0"
down_revision: Union[str, None] = "i4y7z0u6v8w9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "message_annotations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("message_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        # workspace_id materialised so aggregations don't have to
        # join through messages → conversations → workspaces every
        # time. Set via trigger or service at write time.
        sa.Column("workspace_id", sa.UUID(), nullable=True),
        # -1 = thumbs down, +1 = thumbs up. No 0/neutral — neutral
        # means no annotation at all (just delete the row).
        sa.Column("rating", sa.SmallInteger(), nullable=False),
        # Free-text "why?" — shown when rating=-1. Optional even
        # then because not every user wants to write it.
        sa.Column("feedback", sa.Text(), nullable=True),
        # What the user wishes the model HAD said — gold for
        # fine-tuning later (JSONL export with input/output pairs).
        sa.Column("expected_response", sa.Text(), nullable=True),
        # Free-form tags for slicing the dashboard:
        # "hallucination", "off-topic", "format", "tone", …
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.String(length=64)),
            nullable=False,
            server_default=sa.text("'{}'::varchar[]"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("rating IN (-1, 1)", name="ck_annotation_rating"),
        sa.ForeignKeyConstraint(
            ["message_id"], ["messages.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        # One annotation per (message, user) — repeat ratings are
        # an UPDATE, not an INSERT.
        sa.UniqueConstraint(
            "message_id", "user_id", name="uq_annotation_message_user"
        ),
    )
    # Workspace-level aggregations are the dashboard hot path.
    op.create_index(
        "ix_annotations_workspace_created",
        "message_annotations",
        ["workspace_id", sa.text("created_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_annotations_workspace_created", table_name="message_annotations"
    )
    op.drop_table("message_annotations")
