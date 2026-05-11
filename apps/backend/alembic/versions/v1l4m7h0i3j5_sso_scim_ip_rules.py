"""SSO configurations + SCIM tokens + workspace IP rules (Phase 1.3 Block 1)

Three additive tables — enterprise auth foundation.

  sso_configurations: one row per org per IdP. Stores SAML and OIDC
  config in the same table since most fields are common (display
  name, default_role, JIT toggle, attribute mapping). Provider-
  specific columns are nullable.

  scim_tokens: bearer-style tokens for the IdP to call SCIM v2
  endpoints. Hashed at rest (SHA-256). One token can be active per
  org at a time — rotate by issuing a new + revoking the old.

  workspace_ip_rules: CIDR allowlist enforced at the auth dep when
  any rule exists for the active workspace. Empty list = no
  restriction.

Revision ID: v1l4m7h0i3j5
Revises: u0k3l6g9h2i4
Create Date: 2026-05-11 06:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "v1l4m7h0i3j5"
down_revision: Union[str, None] = "u0k3l6g9h2i4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sso_configurations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        # 'saml' or 'oidc' — validated at the service layer.
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        # ── SAML — all nullable; populated only when provider='saml'
        sa.Column("saml_idp_entity_id", sa.Text(), nullable=True),
        sa.Column("saml_idp_sso_url", sa.Text(), nullable=True),
        sa.Column("saml_idp_x509_cert", sa.Text(), nullable=True),
        sa.Column("saml_sp_entity_id", sa.Text(), nullable=True),
        # ── OIDC — all nullable; populated only when provider='oidc'.
        # client_secret is Fernet-encrypted (uses ENCRYPTION_KEY).
        sa.Column("oidc_issuer", sa.Text(), nullable=True),
        sa.Column("oidc_client_id", sa.String(length=255), nullable=True),
        sa.Column("oidc_client_secret_encrypted", sa.Text(), nullable=True),
        # Allow operators to broaden the scope set if the IdP requires it
        # (e.g. Azure tenant-specific roles). Defaults to OIDC standard.
        sa.Column(
            "oidc_scopes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("""'["openid", "email", "profile"]'::jsonb"""),
        ),
        # ── Common
        # Role inserted on the auto-created WorkspaceMember row for
        # JIT-provisioned users. Must be a known workspace role string.
        sa.Column(
            "default_role",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'editor'"),
        ),
        sa.Column(
            "jit_provisioning",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        # Map IdP claim → our user field. Example for Azure AD:
        # {"email": "mail", "full_name": "displayName"}
        sa.Column(
            "attribute_mapping",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
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
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        # One config per (org, provider). Lets an org run SAML + OIDC
        # in parallel (uncommon but legal) while preventing duplicates.
        sa.UniqueConstraint("organization_id", "provider", name="uq_sso_org_provider"),
    )
    op.create_index(
        op.f("ix_sso_configurations_organization_id"),
        "sso_configurations",
        ["organization_id"],
        unique=False,
    )

    # ── SCIM bearer tokens ────────────────────────────────────────
    op.create_table(
        "scim_tokens",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        # Human label so admins can identify which IdP is using each token.
        sa.Column("name", sa.String(length=255), nullable=False),
        # SHA-256 hex of the plaintext token. Unique for lookup.
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_scim_tokens_hash"),
    )
    op.create_index(
        op.f("ix_scim_tokens_organization_id"),
        "scim_tokens",
        ["organization_id"],
        unique=False,
    )

    # ── Workspace IP allowlist ────────────────────────────────────
    op.create_table(
        "workspace_ip_rules",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        # CIDR column — Postgres-native; stored as text fallback on
        # backends that don't support it (we mandate Postgres, so fine).
        sa.Column("cidr", postgresql.CIDR(), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_workspace_ip_rules_workspace_id"),
        "workspace_ip_rules",
        ["workspace_id"],
        unique=False,
    )

    # ── MFA columns on users (Block 3 uses these — added here so
    # ── the schema is one logical step instead of two)
    op.add_column(
        "users",
        # Fernet-encrypted TOTP secret. NULL = TOTP not enrolled.
        sa.Column("totp_secret_encrypted", sa.Text(), nullable=True),
    )
    op.add_column(
        "users",
        # JSONB array of single-use backup codes (hashed). Each consumed
        # code is removed from the array.
        sa.Column(
            "mfa_backup_codes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "mfa_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    # Workspace-level MFA enforcement — read at the auth dep.
    op.add_column(
        "workspaces",
        sa.Column(
            "force_mfa",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("workspaces", "force_mfa")
    op.drop_column("users", "mfa_enabled")
    op.drop_column("users", "mfa_backup_codes")
    op.drop_column("users", "totp_secret_encrypted")
    op.drop_index(op.f("ix_workspace_ip_rules_workspace_id"), table_name="workspace_ip_rules")
    op.drop_table("workspace_ip_rules")
    op.drop_index(op.f("ix_scim_tokens_organization_id"), table_name="scim_tokens")
    op.drop_table("scim_tokens")
    op.drop_index(op.f("ix_sso_configurations_organization_id"), table_name="sso_configurations")
    op.drop_table("sso_configurations")
