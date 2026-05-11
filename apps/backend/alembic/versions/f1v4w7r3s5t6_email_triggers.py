"""email_triggers table (Phase 2.4 Block 2)

A workflow can have many email triggers, each binding to one IMAP
mailbox. Polling worker walks every enabled row, fetches messages
newer than ``last_seen_uid``, and kicks off the workflow.

Why a separate table (vs. workflow_node config):
  - IMAP password lives here and needs encryption-at-rest — easier
    to enforce when the column is dedicated.
  - One table to scan in the poll loop, even with thousands of
    workflows.
  - ``last_seen_uid`` is mutable cursor state that doesn't belong
    on a "config" JSONB.

Revision ID: f1v4w7r3s5t6
Revises: e0u3v6q2r4s5
Create Date: 2026-05-11 17:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "f1v4w7r3s5t6"
down_revision: Union[str, None] = "e0u3v6q2r4s5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "email_triggers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workflow_id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        # Display name for the FE table — multiple triggers per
        # workflow are allowed (separate inboxes) so a name disambiguates.
        sa.Column("name", sa.String(length=255), nullable=False),
        # Connection parameters. ``imap_use_ssl`` toggles SSL on
        # connection (port 993 vs 143). ``imap_port`` lets self-hosted
        # mail servers on non-standard ports work without code change.
        sa.Column("imap_host", sa.String(length=255), nullable=False),
        sa.Column("imap_port", sa.Integer(), nullable=False, server_default="993"),
        sa.Column(
            "imap_use_ssl",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("imap_username", sa.String(length=255), nullable=False),
        # Fernet-encrypted IMAP password. NEVER returned to the FE.
        sa.Column("imap_password_enc", sa.Text(), nullable=False),
        # Mailbox to poll. "INBOX" is the default; configurable so
        # users can route a label/folder to one workflow.
        sa.Column(
            "imap_folder",
            sa.String(length=255),
            nullable=False,
            server_default="INBOX",
        ),
        # Poll interval. Bounded sanity in the service layer
        # (min 60, max 3600) to avoid hammering free IMAP providers.
        sa.Column(
            "poll_interval_seconds",
            sa.Integer(),
            nullable=False,
            server_default="300",
        ),
        # Whether to mark messages as ``\Seen`` after dispatching.
        # When False, the same message can be re-fetched until the
        # uid cursor advances — useful for tracing/replays.
        sa.Column(
            "mark_seen",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        # Cursor — IMAP UID of the last message we dispatched.
        # NULL means "we haven't fetched anything yet; start from
        # max-uid-at-first-poll" so a freshly-bound mailbox doesn't
        # replay years of history.
        sa.Column("last_seen_uid", sa.BigInteger(), nullable=True),
        sa.Column("last_polled_at", sa.TIMESTAMP(timezone=True), nullable=True),
        # last_error / last_error_at — surfaced in the UI so users
        # can debug auth failures without tailing logs. Cleared on
        # next successful poll.
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_error_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
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
        sa.ForeignKeyConstraint(
            ["workflow_id"], ["workflows.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_email_triggers_workflow",
        "email_triggers",
        ["workflow_id"],
        unique=False,
    )
    op.create_index(
        "ix_email_triggers_workspace",
        "email_triggers",
        ["workspace_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_email_triggers_workspace", table_name="email_triggers")
    op.drop_index("ix_email_triggers_workflow", table_name="email_triggers")
    op.drop_table("email_triggers")
