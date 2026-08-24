"""Add entry_jira_links table for KB ↔ Jira associations.

Revision ID: 005_entry_jira_links
Revises: 004_embedding_vector_1024
Create Date: 2026-06-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_entry_jira_links"
down_revision: Union[str, None] = "004_embedding_vector_1024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "entry_jira_links",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("entry_id", sa.UUID(), nullable=False),
        sa.Column("jira_key", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["entry_id"], ["entries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entry_id", "jira_key", name="uq_entry_jira_links_entry_key"),
    )
    op.create_index("ix_entry_jira_links_jira_key", "entry_jira_links", ["jira_key"])


def downgrade() -> None:
    op.drop_index("ix_entry_jira_links_jira_key", table_name="entry_jira_links")
    op.drop_table("entry_jira_links")
