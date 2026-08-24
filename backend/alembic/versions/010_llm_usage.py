"""Add llm_usage table for tracking token consumption and cost.

Revision ID: 010_llm_usage
Revises: 009_seed_templates
Create Date: 2026-07-16
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "010_llm_usage"
down_revision: Union[str, None] = "009_seed_templates"


def upgrade() -> None:
    op.create_table(
        "llm_usage",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("route", sa.String(length=255), nullable=False),
        sa.Column("model_id", sa.String(length=255), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_llm_usage_created_at", "llm_usage", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_llm_usage_created_at", table_name="llm_usage")
    op.drop_table("llm_usage")
