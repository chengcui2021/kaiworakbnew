"""List knowledge base entries with filters and pagination."""

from __future__ import annotations

import logging

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from uuid import UUID

from app.persistence.constants import LIST_DEFAULT_LIMIT
from app.persistence.entry_response import entry_to_response
from app.persistence.models import ComponentName, Entry, EntryStatus, EntryTag, EntryType, Tag
from app.persistence.schemas import EntryListResponse
from app.persistence.tag_service import normalize_tag_name

logger = logging.getLogger(__name__)


def _apply_entry_filters(
    stmt: Select,
    *,
    workstream_id: UUID | None,
    unassigned: bool,
    component: ComponentName | None,
    entry_type: EntryType | None,
    entry_status: EntryStatus | None,
    tag_name: str | None,
) -> Select:
    if unassigned:
        stmt = stmt.where(Entry.workstream_id.is_(None))
    elif workstream_id is not None:
        stmt = stmt.where(Entry.workstream_id == workstream_id)
    if component is not None:
        stmt = stmt.where(Entry.component_name == component)
    if entry_type is not None:
        stmt = stmt.where(Entry.entry_type == entry_type)
    if entry_status is not None:
        stmt = stmt.where(Entry.status == entry_status)
    if tag_name is not None:
        stmt = stmt.join(Entry.entry_tags).join(EntryTag.tag).where(Tag.name == tag_name)
    return stmt


async def list_entries(
    db: AsyncSession,
    *,
    workstream_id: UUID | None = None,
    unassigned: bool = False,
    component: ComponentName | None = None,
    entry_type: EntryType | None = None,
    entry_status: EntryStatus | None = None,
    tag: str | None = None,
    limit: int = LIST_DEFAULT_LIMIT,
    offset: int = 0,
) -> EntryListResponse:
    """Return entries ordered by ``created_at`` descending with total count."""
    tag_name = normalize_tag_name(tag) if tag and tag.strip() else None
    filters = {
        "workstream_id": workstream_id,
        "unassigned": unassigned,
        "component": component,
        "entry_type": entry_type,
        "entry_status": entry_status,
        "tag_name": tag_name,
    }

    count_stmt = select(func.count()).select_from(Entry)
    count_stmt = _apply_entry_filters(count_stmt, **filters)

    list_stmt = (
        select(Entry)
        .options(selectinload(Entry.entry_tags).selectinload(EntryTag.tag))
        .order_by(Entry.created_at.desc())
    )
    list_stmt = _apply_entry_filters(list_stmt, **filters)
    list_stmt = list_stmt.offset(offset).limit(limit)

    try:
        total = await db.scalar(count_stmt)
        rows = (await db.execute(list_stmt)).scalars().unique().all()
    except Exception:
        logger.exception("Failed to list entries")
        raise

    return EntryListResponse(
        entries=[entry_to_response(row) for row in rows],
        total=int(total or 0),
        limit=limit,
        offset=offset,
    )
