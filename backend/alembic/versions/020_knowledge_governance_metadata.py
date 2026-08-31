"""Add first-class engineering knowledge governance metadata.

Revision ID: 020_knowledge_governance_meta
Revises: 019_knowledge_usage_feedback
"""
from alembic import op
import sqlalchemy as sa

revision = "020_knowledge_governance_meta"
down_revision = "019_knowledge_usage_feedback"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("entries", sa.Column("knowledge_kind", sa.String(length=64), nullable=False, server_default="documentation"))
    op.add_column("entries", sa.Column("applies_to", sa.String(length=128), nullable=True))
    op.add_column("entries", sa.Column("priority", sa.Integer(), nullable=False, server_default="100"))
    op.create_index("ix_entries_governance_kind", "entries", ["knowledge_kind", "owner_scope", "status"] )

def downgrade():
    op.drop_index("ix_entries_governance_kind", table_name="entries")
    op.drop_column("entries", "priority")
    op.drop_column("entries", "applies_to")
    op.drop_column("entries", "knowledge_kind")
