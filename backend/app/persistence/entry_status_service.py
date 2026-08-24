"""Update entry lifecycle status."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.models import Entry, EntryPatchStatus, EntryStatus
from app.persistence.schemas import EntryResponse

logger = logging.getLogger(__name__)


class EntryNotFoundError(Exception):
    """Raised when no entry exists for the given id."""


async def update_entry_status(
    db: AsyncSession,
    entry_id: UUID,
    new_status: EntryPatchStatus,
) -> EntryResponse:
    """Set entry status and persist (``updated_at`` refreshed via DB trigger on UPDATE)."""
    result = await db.execute(select(Entry).where(Entry.id == entry_id))
    entry = result.scalar_one_or_none()
    if entry is None:
        raise EntryNotFoundError(str(entry_id))

    entry.status = EntryStatus(new_status.value)
    try:
        await db.commit()
        await db.refresh(entry)
    except Exception:
        await db.rollback()
        logger.exception("Failed to update entry status for id=%s", entry_id)
        raise

    return EntryResponse.model_validate(entry)
