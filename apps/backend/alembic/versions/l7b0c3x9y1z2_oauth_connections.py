"""oauth_connections + oauth_states tables (connector OAuth flow)

3-legged OAuth flow for KB connectors. Distinct from the login
OAuth (auth_tokens) — these tokens grant access to a tenant's
external data source, not to our own app.

Revision ID: l7b0c3x9y1z2
Revises: k6a9b2w8x0y1
Create Date: 2026-05-12 14:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "l7b0c3x9y1z2"
down_revision: Union[str, None] = "k6a9b2w8x0y1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "oauth_connections",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        # Provider slug — "slack" | "notion" | "dropbox" | …
        # Matches the connector-provider registry keys.
        sa.Column("provider", sa.String(length=32), nullable=False),
        # Display label shown in the picker: e.g. Slack workspace
        # name + team domain, Notion workspace name, Dropbox email.
        sa.Column("account_label", sa.Text(), nullable=True),
        # Provider-side account / tenant id used by connectors to
        # build API requests (Slack team_id, Notion workspace_id,
        # Dropbox account_id, etc.).
        sa.Column("external_account_id", sa.String(length=255), nullable=True),
        # Fernet-encrypted token material. Never returned to the FE.
        sa.Column("access_token_enc", sa.Text(), nullable=False),
        sa.Column("refresh_token_enc", sa.Text(), nullable=True),
        # Absolute expiry of the access token; NULL when the
        # provider issues long-lived tokens (Slack, Notion).
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        # Granted scope string — useful for debugging "why doesn't
        # my connector see file X".
        sa.Column("scope", sa.Text(), nullable=True),
        # Whole token response — provider-specific extra fields
        # (bot_user_id, workspace_icon, …) kept for forensics.
        sa.Column(
            "raw_response",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
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
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        # One connection per (workspace, provider, external account).
        # Re-connecting the same Slack workspace upserts in place
        # instead of duplicating rows.
        sa.UniqueConstraint(
            "workspace_id",
            "provider",
            "external_account_id",
            name="uq_oauth_ws_provider_account",
        ),
    )
    op.create_index(
        "ix_oauth_connections_workspace",
        "oauth_connections",
        ["workspace_id"],
        unique=False,
    )

    # Short-lived state tokens for the OAuth dance. Persisted (not
    # in-memory) so a multi-worker deploy doesn't break the flow
    # when callback hits a different worker than start.
    op.create_table(
        "oauth_states",
        sa.Column("state", sa.String(length=128), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        # Frontend path the BE redirects back to after the
        # callback completes (e.g. /knowledge/abc?tab=connectors).
        sa.Column("return_to", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "expires_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("state"),
    )


def downgrade() -> None:
    op.drop_table("oauth_states")
    op.drop_index(
        "ix_oauth_connections_workspace", table_name="oauth_connections"
    )
    op.drop_table("oauth_connections")
