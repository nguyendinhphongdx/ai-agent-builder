"""Backfill organization_members for users with only workspace_members.

The Hub refactor surfaces orgs via the user's ``organization_members``
rows. Pre-refactor flows added a user as ``workspace_members`` of a
workspace owned by another org *without* also adding them to that
org's members table, so those orgs never show in the org switcher.

This migration inserts a viewer-role org_member for every
(user, organization) pair that has at least one workspace_members row
but no organization_members row.

Revision ID: f5j2g8e3h6c0
Revises: e4i1f7d2g5b9
Create Date: 2026-05-16 09:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "f5j2g8e3h6c0"
down_revision: Union[str, None] = "e4i1f7d2g5b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO organization_members (id, organization_id, user_id, role, joined_at)
        SELECT
            gen_random_uuid(),
            w.organization_id,
            wm.user_id,
            'viewer',
            COALESCE(MIN(wm.joined_at), NOW())
        FROM   workspace_members wm
        JOIN   workspaces w        ON w.id = wm.workspace_id
        WHERE  NOT EXISTS (
            SELECT 1 FROM organization_members om
            WHERE  om.organization_id = w.organization_id
            AND    om.user_id = wm.user_id
        )
        GROUP  BY w.organization_id, wm.user_id
        """
    )


def downgrade() -> None:
    # Not reversible safely — we'd have to distinguish "added by this
    # backfill" from "viewer-role org_member added the normal way".
    # No-op to avoid corrupting org membership on rollback.
    pass
