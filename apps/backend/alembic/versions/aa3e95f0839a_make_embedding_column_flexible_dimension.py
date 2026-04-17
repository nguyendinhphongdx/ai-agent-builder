"""make embedding column flexible dimension

Revision ID: aa3e95f0839a
Revises: 1d745494df26
Create Date: 2026-04-13 13:07:33.546829

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'aa3e95f0839a'
down_revision: Union[str, None] = '1d745494df26'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Change from vector(1536) to vector (no fixed dimension)
    op.execute("ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector USING embedding::vector")


def downgrade() -> None:
    op.execute("ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(1536) USING embedding::vector(1536)")
