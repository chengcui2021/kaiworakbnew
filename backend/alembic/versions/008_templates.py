"""Add templates table for reusable document templates.

Revision ID: 008_templates
Revises: 007_entry_title
Create Date: 2026-07-16
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "008_templates"
down_revision: Union[str, None] = "007_entry_title"


def upgrade() -> None:
    op.create_table(
        "templates",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
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
        sa.UniqueConstraint("name", name="uq_templates_name"),
    )
    op.create_index("ix_templates_name", "templates", ["name"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_templates_name", table_name="templates")
    op.drop_table("templates")
