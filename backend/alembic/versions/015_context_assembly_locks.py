"""Persist Context Assembly Locks for governed downstream Project Run.

Revision ID: 015_context_assembly_locks
Revises: 014_workstream_restore
Create Date: 2026-08-17
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "015_context_assembly_locks"
down_revision: Union[str, None] = "014_workstream_restore"


def upgrade() -> None:
    op.create_table(
        "context_assembly_locks",
        sa.Column("lock_id", sa.String(length=128), nullable=False),
        sa.Column("context_hash", sa.String(length=128), nullable=False),
        sa.Column("lock_payload", sa.JSON(), nullable=False),
        sa.Column("assembly_payload", sa.JSON(), nullable=False),
        sa.Column("request_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("lock_id"),
    )
    op.create_index(
        "ix_context_assembly_locks_context_hash",
        "context_assembly_locks",
        ["context_hash"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_context_assembly_locks_context_hash", table_name="context_assembly_locks")
    op.drop_table("context_assembly_locks")
