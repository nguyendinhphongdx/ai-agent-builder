"""workflows + nodes + edges + runs workspace_id (Phase 1.1 step 2 — group C)

Closes step-2: last 4 resource tables get the workspace_id column.
Same nullable-FK-CASCADE shape as previous groups. Backfill (step 3)
stamps every row from each workflow's user_id → personal workspace.

Revision ID: r7h9i3d6e8f0
Revises: q6g8h2c5d7e9
Create Date: 2026-05-11 02:30:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "r7h9i3d6e8f0"
down_revision: Union[str, None] = "q6g8h2c5d7e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TABLES = [
    ("workflows", "fk_workflows_workspace_id", "ix_workflows_workspace_id"),
    (
        "workflow_nodes",
        "fk_workflow_nodes_workspace_id",
        "ix_workflow_nodes_workspace_id",
    ),
    (
        "workflow_edges",
        "fk_workflow_edges_workspace_id",
        "ix_workflow_edges_workspace_id",
    ),
    (
        "workflow_runs",
        "fk_workflow_runs_workspace_id",
        "ix_workflow_runs_workspace_id",
    ),
]


def upgrade() -> None:
    for table, fk_name, ix_name in _TABLES:
        op.add_column(table, sa.Column("workspace_id", sa.UUID(), nullable=True))
        op.create_foreign_key(
            fk_name, table, "workspaces", ["workspace_id"], ["id"], ondelete="CASCADE"
        )
        op.create_index(op.f(ix_name), table, ["workspace_id"], unique=False)


def downgrade() -> None:
    for table, fk_name, ix_name in reversed(_TABLES):
        op.drop_index(op.f(ix_name), table_name=table)
        op.drop_constraint(fk_name, table, type_="foreignkey")
        op.drop_column(table, "workspace_id")
