"""governed learning candidates

Revision ID: 016_governed_learning
Revises: 015_context_assembly_locks
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision="016_governed_learning"
down_revision="015_context_assembly_locks"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("learning_entries",
      sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
      sa.Column("tenant_id",sa.String(255),nullable=False,server_default="default"),
      sa.Column("workspace_id",sa.String(255),nullable=False,server_default="default"),
      sa.Column("repository_id",sa.Text(),nullable=False,server_default=""),
      sa.Column("knowledge_type",sa.String(32),nullable=False,server_default="procedural"),
      sa.Column("scope",sa.String(32),nullable=False,server_default="repository"),
      sa.Column("observation",sa.Text(),nullable=False),
      sa.Column("fingerprint",sa.String(64),nullable=False),
      sa.Column("status",sa.String(32),nullable=False,server_default="candidate"),
      sa.Column("confidence",sa.Integer(),nullable=False,server_default="0"),
      sa.Column("source_run_id",sa.String(255),nullable=False,server_default=""),
      sa.Column("source_commit",sa.String(255),nullable=False,server_default=""),
      sa.Column("evidence",postgresql.JSONB(astext_type=sa.Text()),nullable=False,server_default=sa.text("'{}'::jsonb")),
      sa.Column("provenance",postgresql.JSONB(astext_type=sa.Text()),nullable=False,server_default=sa.text("'{}'::jsonb")),
      sa.Column("created_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),
      sa.Column("validated_at",sa.DateTime(timezone=True),nullable=True))
    op.create_index("ix_learning_scope","learning_entries",["tenant_id","workspace_id","repository_id"]); op.create_index("ix_learning_status","learning_entries",["status"]); op.create_index("ix_learning_fingerprint","learning_entries",["fingerprint"])

def downgrade():
    op.drop_table("learning_entries")
