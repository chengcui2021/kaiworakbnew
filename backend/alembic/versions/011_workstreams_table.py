"""Create workstreams table with seed data.

Revision ID: 011_workstreams_table
Revises: 010_llm_usage
Create Date: 2026-08-06
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "011_workstreams_table"
down_revision: Union[str, None] = "010_llm_usage"


# Deterministic UUIDs for seed data so migration is idempotent.
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
    table = op.create_table(
        "workstreams",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), server_default=sa.text("''"), nullable=False),
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
    op.create_index("ix_workstreams_name", "workstreams", ["name"], unique=True)

    op.bulk_insert(
        table,
        [
            {"id": ws["id"], "name": ws["name"], "description": ws["description"]}
            for ws in _SEED_WORKSTREAMS
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_workstreams_name", table_name="workstreams")
    op.drop_table("workstreams")
