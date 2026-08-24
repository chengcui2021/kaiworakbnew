"""Add lifecycle status values for PATCH /entries/{id}.

Revision ID: 003_entry_status_lifecycle
Revises: 002_entry_status_open
Create Date: 2026-05-20

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_entry_status_lifecycle"
down_revision: Union[str, None] = "002_entry_status_open"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW_STATUSES = ("resolved", "deferred", "superseded")


def upgrade() -> None:
    for value in _NEW_STATUSES:
        op.execute(sa.text(f"ALTER TYPE entry_status ADD VALUE IF NOT EXISTS '{value}'"))


def downgrade() -> None:
    # PostgreSQL cannot drop individual enum values safely; leave type as-is.
    pass
