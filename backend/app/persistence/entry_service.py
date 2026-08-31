"""Full entry update and deletion."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.persistence.entry_response import entry_to_response
from app.persistence.entry_status_service import EntryNotFoundError
from app.persistence.models import Entry, EntryTag
from app.persistence.schemas import EntryResponse, EntryUpdate

logger = logging.getLogger(__name__)


async def update_entry(
    db: AsyncSession,
    entry_id: UUID,
    data: EntryUpdate,
    new_embedding: list[float] | None,
) -> EntryResponse:
    """Apply full update to an entry.

    *new_embedding* should be the freshly generated vector when content changed,
    or ``None`` to keep the existing embedding.
    """
    result = await db.execute(
        select(Entry)
        .where(Entry.id == entry_id)
        .options(selectinload(Entry.entry_tags).selectinload(EntryTag.tag))
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise EntryNotFoundError(str(entry_id))

    entry.entry_type = data.entry_type
    entry.component_name = data.component_name
    entry.title = data.title
    entry.content = data.content
    entry.source = data.source
    entry.author = data.author
    entry.status = data.status
    entry.workstream_id = data.workstream_id
    entry.owner_scope = data.owner_scope
    entry.tenant_id = data.tenant_id
    entry.workspace_id = data.workspace_id
    entry.repository_id = data.repository_id
    entry.knowledge_kind = data.knowledge_kind
    entry.applies_to = data.applies_to
    entry.priority = data.priority

    if new_embedding is not None:
        entry.embedding = new_embedding

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception("Failed to update entry id=%s", entry_id)
        raise

    # Re-query with eager loading so entry_to_response can access tags
    result = await db.execute(
        select(Entry)
        .where(Entry.id == entry_id)
        .options(selectinload(Entry.entry_tags).selectinload(EntryTag.tag))
    )
    entry = result.scalar_one_or_none()

    return entry_to_response(entry)


async def delete_entry(
    db: AsyncSession,
    entry_id: UUID,
) -> None:
    """Delete an entry by ID. Raises EntryNotFoundError if not found."""
    result = await db.execute(select(Entry).where(Entry.id == entry_id))
    entry = result.scalar_one_or_none()
    if entry is None:
        raise EntryNotFoundError(str(entry_id))

    await db.delete(entry)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception("Failed to delete entry id=%s", entry_id)
        raise
