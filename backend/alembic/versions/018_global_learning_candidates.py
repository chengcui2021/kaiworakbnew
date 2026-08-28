"""Governed cross-customer learning inbox.

Revision ID: 018_global_learning_candidates
Revises: 017_cloud_multi_tenant_scopes
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "018_global_learning_candidates"
down_revision = "017_cloud_multi_tenant_scopes"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "global_learning_candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("source_learning_entry_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("learning_entries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_tenant_id", sa.String(255), nullable=False),
        sa.Column("source_workspace_id", sa.String(255), nullable=False, server_default="default"),
        sa.Column("source_repository_id", sa.Text(), nullable=False, server_default=""),
        sa.Column("knowledge_type", sa.String(32), nullable=False, server_default="procedural"),
        sa.Column("sanitised_observation", sa.Text(), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("evidence_summary", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("privacy_status", sa.String(32), nullable=False, server_default="sanitised"),
        sa.Column("review_status", sa.String(32), nullable=False, server_default="ready_for_review"),
        sa.Column("reviewed_by", sa.String(255), nullable=False, server_default=""),
        sa.Column("review_note", sa.Text(), nullable=False, server_default=""),
        sa.Column("approved_entry_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entries.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_global_learning_review_status", "global_learning_candidates", ["review_status"])
    op.create_index("ix_global_learning_fingerprint", "global_learning_candidates", ["fingerprint"])
    op.create_index("ix_global_learning_source_tenant", "global_learning_candidates", ["source_tenant_id"])

def downgrade():
    op.drop_table("global_learning_candidates")
