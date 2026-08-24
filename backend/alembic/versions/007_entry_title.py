"""Add title column to entries.

Revision ID: 007_entry_title
Revises: 006_entry_tags
Create Date: 2026-06-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_entry_title"
down_revision: Union[str, None] = "006_entry_tags"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "entries",
        sa.Column("title", sa.String(length=255), nullable=False, server_default=""),
    )
    op.alter_column("entries", "title", server_default=None)


def downgrade() -> None:
    op.drop_column("entries", "title")
