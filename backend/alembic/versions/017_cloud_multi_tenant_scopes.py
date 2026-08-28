"""Kaiwora Cloud multi-tenant foundation and knowledge scopes.

Revision ID: 017_cloud_multi_tenant_scopes
Revises: 016_governed_learning
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "017_cloud_multi_tenant_scopes"
down_revision = "016_governed_learning"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"], unique=True)
    op.create_table(
        "cloud_workspaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_cloud_workspace_tenant_slug"),
    )
    op.create_index("ix_cloud_workspaces_tenant", "cloud_workspaces", ["tenant_id"])
    op.create_table(
        "cloud_repositories",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cloud_workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_id", sa.String(500), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("default_branch", sa.String(300), nullable=False, server_default="main"),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "workspace_id", "external_id", name="uq_cloud_repo_owner_external"),
    )
    op.create_index("ix_cloud_repositories_scope", "cloud_repositories", ["tenant_id", "workspace_id"])

    op.add_column("entries", sa.Column("owner_scope", sa.String(32), nullable=False, server_default="global"))
    op.add_column("entries", sa.Column("tenant_id", sa.String(255), nullable=True))
    op.add_column("entries", sa.Column("workspace_id", sa.String(255), nullable=True))
    op.add_column("entries", sa.Column("repository_id", sa.Text(), nullable=True))
    op.create_index("ix_entries_owner_scope", "entries", ["owner_scope", "tenant_id", "workspace_id", "repository_id"])

    op.add_column("context_assembly_locks", sa.Column("tenant_id", sa.String(255), nullable=False, server_default="default"))
    op.add_column("context_assembly_locks", sa.Column("workspace_id", sa.String(255), nullable=False, server_default="default"))
    op.add_column("context_assembly_locks", sa.Column("repository_id", sa.Text(), nullable=False, server_default=""))
    op.create_index("ix_context_locks_tenant", "context_assembly_locks", ["tenant_id"])
    op.create_index("ix_context_locks_workspace", "context_assembly_locks", ["workspace_id"])


def downgrade():
    op.drop_index("ix_context_locks_workspace", table_name="context_assembly_locks")
    op.drop_index("ix_context_locks_tenant", table_name="context_assembly_locks")
    op.drop_column("context_assembly_locks", "repository_id")
    op.drop_column("context_assembly_locks", "workspace_id")
    op.drop_column("context_assembly_locks", "tenant_id")
    op.drop_index("ix_entries_owner_scope", table_name="entries")
    op.drop_column("entries", "repository_id")
    op.drop_column("entries", "workspace_id")
    op.drop_column("entries", "tenant_id")
    op.drop_column("entries", "owner_scope")
    op.drop_table("cloud_repositories")
    op.drop_table("cloud_workspaces")
    op.drop_table("tenants")
