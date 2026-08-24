"""Add nullable workstream_id FK to entries table.

Revision ID: 012_entries_workstream_id
Revises: 011_workstreams_table
Create Date: 2026-08-06
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "012_entries_workstream_id"
down_revision: Union[str, None] = "011_workstreams_table"


def upgrade() -> None:
    op.add_column(
        "entries",
        sa.Column(
            "workstream_id",
            sa.UUID(),
            sa.ForeignKey("workstreams.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_entries_workstream_id", "entries", ["workstream_id"])


def downgrade() -> None:
    op.drop_index("ix_entries_workstream_id", table_name="entries")
    op.drop_column("entries", "workstream_id")
