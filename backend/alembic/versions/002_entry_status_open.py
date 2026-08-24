"""Add 'open' value to entry_status enum (Phase 1 default for new entries).

Revision ID: 002_entry_status_open
Revises: 001_initial_entries_schema
Create Date: 2026-05-14

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_entry_status_open"
down_revision: Union[str, None] = "001_initial_entries_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TYPE entry_status ADD VALUE IF NOT EXISTS 'open'"))


def downgrade() -> None:
    # PostgreSQL cannot drop individual enum values safely; leave type as-is.
    pass
