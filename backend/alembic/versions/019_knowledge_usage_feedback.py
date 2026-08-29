"""Knowledge outcome feedback for learned context selection.
Revision ID: 019_knowledge_usage_feedback
Revises: 018_global_learning_candidates
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision='019_knowledge_usage_feedback'; down_revision='018_global_learning_candidates'; branch_labels=None; depends_on=None
def upgrade():
    op.create_table('knowledge_usage',
        sa.Column('id',postgresql.UUID(as_uuid=True),server_default=sa.text('gen_random_uuid()'),primary_key=True),
        sa.Column('entry_id',postgresql.UUID(as_uuid=True),sa.ForeignKey('entries.id',ondelete='CASCADE'),nullable=False),
        sa.Column('tenant_id',sa.String(255),nullable=False),sa.Column('workspace_id',sa.String(255),nullable=False,server_default='default'),sa.Column('repository_id',sa.Text(),nullable=False,server_default=''),
        sa.Column('run_id',sa.String(255),nullable=False),sa.Column('task_type',sa.String(64),nullable=False,server_default='engineering'),sa.Column('outcome',sa.String(32),nullable=False),sa.Column('repair_count',sa.Integer(),nullable=False,server_default='0'),sa.Column('relevance',sa.Integer(),nullable=False,server_default='50'),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()))
    op.create_index('ix_knowledge_usage_entry','knowledge_usage',['entry_id']); op.create_index('ix_knowledge_usage_scope','knowledge_usage',['tenant_id','workspace_id','repository_id'])
def downgrade(): op.drop_table('knowledge_usage')
