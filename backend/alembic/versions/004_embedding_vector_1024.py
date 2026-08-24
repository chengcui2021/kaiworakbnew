"""Resize embedding column for Titan Text Embeddings V2 (1024 dimensions).

Revision ID: 004_embedding_vector_1024
Revises: 003_entry_status_lifecycle
Create Date: 2026-05-20

Titan Embed V2 supports 256, 512, or 1024 only — not 384 (MiniLM legacy size).
Existing vectors are cleared; re-create entries or re-embed after upgrade.

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_embedding_vector_1024"
down_revision: Union[str, None] = "003_entry_status_lifecycle"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS ix_entries_embedding_hnsw"))
    op.execute(sa.text("UPDATE entries SET embedding = NULL"))
    op.execute(sa.text("ALTER TABLE entries ALTER COLUMN embedding TYPE vector(1024)"))
    op.execute(
        sa.text(
            """
            CREATE INDEX ix_entries_embedding_hnsw ON entries
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS ix_entries_embedding_hnsw"))
    op.execute(sa.text("UPDATE entries SET embedding = NULL"))
    op.execute(sa.text("ALTER TABLE entries ALTER COLUMN embedding TYPE vector(384)"))
    op.execute(
        sa.text(
            """
            CREATE INDEX ix_entries_embedding_hnsw ON entries
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
            """
        )
    )
