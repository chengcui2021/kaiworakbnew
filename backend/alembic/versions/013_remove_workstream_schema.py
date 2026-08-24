"""Remove deprecated workstream schema.

Revision ID: 013_remove_workstream_schema
Revises: 012_entries_workstream_id
Create Date: 2026-08-09
"""

from typing import Union

import sqlalchemy as sa
from alembic import op


revision: str = "013_remove_workstream_schema"
down_revision: Union[str, None] = "012_entries_workstream_id"


_SEED_WORKSTREAMS = [
    {
        "id": "00000000-0000-4000-a000-000000000001",
        "name": "Marketing Q1",
        "description": "Q1 marketing campaign knowledge base",
    },
    {
        "id": "00000000-0000-4000-a000-000000000002",
        "name": "Engineering Handbook",
        "description": "Engineering team reference material",
    },
    {
        "id": "00000000-0000-4000-a000-000000000003",
        "name": "Personal Notes",
        "description": "",
    },
]


def upgrade() -> None:
    op.drop_index("ix_entries_workstream_id", table_name="entries")
    op.drop_column("entries", "workstream_id")

    op.drop_index("ix_workstreams_name", table_name="workstreams")
    op.drop_table("workstreams")


def downgrade() -> None:
    workstreams = op.create_table(
        "workstreams",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "description",
            sa.Text(),
            server_default=sa.text("''"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_workstreams_name",
        "workstreams",
        ["name"],
        unique=True,
    )

    op.bulk_insert(workstreams, _SEED_WORKSTREAMS)

    op.add_column(
        "entries",
        sa.Column(
            "workstream_id",
            sa.UUID(),
            sa.ForeignKey("workstreams.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_entries_workstream_id",
        "entries",
        ["workstream_id"],
    )
