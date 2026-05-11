"""workflows.webhook_secret column (Phase 2.4 Block 1)

Distinct from ``webhook_token``:
  webhook_token   URL-embedded — *routes* the request (anyone with
                  the URL can hit it; rotates via /workflows/{id}/
                  webhook-token/rotate).
  webhook_secret  HMAC key — *authenticates* the payload integrity
                  when the node opts in via config.require_signature.
                  Senders compute HMAC-SHA256 over the raw body and
                  include it as ``X-Hub-Signature-256: sha256=<hex>``.

Both nullable so legacy rows don't break — secret stays NULL until
a workflow rotates / requests one. ``require_signature=true`` on a
node whose workflow has no secret returns 503 at receive time.

Revision ID: e0u3v6q2r4s5
Revises: d9t2u5p1q3r4
Create Date: 2026-05-11 16:30:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "e0u3v6q2r4s5"
down_revision: Union[str, None] = "d9t2u5p1q3r4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "workflows",
        sa.Column("webhook_secret", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workflows", "webhook_secret")
