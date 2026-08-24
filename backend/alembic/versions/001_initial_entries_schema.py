"""Initial entries table, PostgreSQL enums, and pgvector.

Revision ID: 001_initial_entries_schema
Revises:
Create Date: 2026-05-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import VECTOR
from sqlalchemy.dialects import postgresql

revision: str = "001_initial_entries_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))

    op.execute(
        sa.text(
            """
            CREATE TYPE entry_type AS ENUM (
                'documentation', 'requirement', 'constraint', 'example', 'other'
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TYPE component_name AS ENUM (
                'ingestion', 'storage', 'retrieval', 'embedding', 'api', 'admin', 'unknown'
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TYPE entry_status AS ENUM (
                'draft', 'pending_review', 'published', 'archived', 'rejected'
            )
            """
        )
    )

    entry_type = postgresql.ENUM(
        "documentation",
        "requirement",
        "constraint",
        "example",
        "other",
        name="entry_type",
        create_type=False,
    )
    component_name = postgresql.ENUM(
        "ingestion",
        "storage",
        "retrieval",
        "embedding",
        "api",
        "admin",
        "unknown",
        name="component_name",
        create_type=False,
    )
    entry_status = postgresql.ENUM(
        "draft",
        "pending_review",
        "published",
        "archived",
        "rejected",
        name="entry_status",
        create_type=False,
    )

    op.create_table(
        "entries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("type", entry_type, nullable=False),
        sa.Column("component", component_name, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("author", sa.String(length=255), nullable=False),
        sa.Column("status", entry_status, nullable=False),
        sa.Column("embedding", VECTOR(384), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name="pk_entries"),
    )

    op.create_index("ix_entries_entry_type", "entries", ["type"], unique=False)
    op.create_index("ix_entries_component", "entries", ["component"], unique=False)
    op.create_index("ix_entries_status", "entries", ["status"], unique=False)
    op.create_index("ix_entries_created_at", "entries", ["created_at"], unique=False)

    op.execute(
        sa.text(
            """
            CREATE INDEX ix_entries_embedding_hnsw ON entries
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
            """
        )
    )

    op.execute(
        sa.text(
            """
            CREATE OR REPLACE FUNCTION entries_touch_updated_at()
            RETURNS TRIGGER AS $$
            BEGIN
              NEW.updated_at = NOW();
              RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER entries_touch_updated_at
            BEFORE UPDATE ON entries
            FOR EACH ROW
            EXECUTE PROCEDURE entries_touch_updated_at()
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP TRIGGER IF EXISTS entries_touch_updated_at ON entries"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS entries_touch_updated_at()"))

    op.execute(sa.text("DROP INDEX IF EXISTS ix_entries_embedding_hnsw"))
    op.drop_index("ix_entries_created_at", table_name="entries")
    op.drop_index("ix_entries_status", table_name="entries")
    op.drop_index("ix_entries_component", table_name="entries")
    op.drop_index("ix_entries_entry_type", table_name="entries")

    op.drop_table("entries")

    op.execute(sa.text("DROP TYPE IF EXISTS entry_status"))
    op.execute(sa.text("DROP TYPE IF EXISTS component_name"))
    op.execute(sa.text("DROP TYPE IF EXISTS entry_type"))

    op.execute(sa.text("DROP EXTENSION IF EXISTS vector"))
