"""Persistent workstream CRUD (PostgreSQL)."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.models import Entry, WorkstreamDB
from app.persistence.schemas import WorkstreamResponse, WorkstreamStatsResponse

logger = logging.getLogger(__name__)


def _ws_to_response(ws: WorkstreamDB, entry_count: int = 0) -> WorkstreamResponse:
    return WorkstreamResponse(
        id=ws.id,
        name=ws.name,
        description=ws.description,
        created_at=ws.created_at,
        updated_at=ws.updated_at,
        entry_count=entry_count,
    )


async def list_workstreams(db: AsyncSession) -> list[WorkstreamResponse]:
    """Return all workstreams with their entry counts."""
    count_sub = (
        select(Entry.workstream_id, func.count().label("cnt"))
        .where(Entry.workstream_id.is_not(None))
        .group_by(Entry.workstream_id)
        .subquery()
    )
    stmt = (
        select(WorkstreamDB, func.coalesce(count_sub.c.cnt, 0).label("entry_count"))
        .outerjoin(count_sub, WorkstreamDB.id == count_sub.c.workstream_id)
        .order_by(WorkstreamDB.created_at)
    )
    rows = (await db.execute(stmt)).all()
    return [_ws_to_response(ws, int(cnt)) for ws, cnt in rows]


async def get_workstream(db: AsyncSession, workstream_id: UUID) -> WorkstreamResponse | None:
    """Return a single workstream or None."""
    ws = await db.get(WorkstreamDB, workstream_id)
    if ws is None:
        return None
    count = await db.scalar(
        select(func.count()).select_from(Entry).where(Entry.workstream_id == workstream_id)
    )
    return _ws_to_response(ws, int(count or 0))


async def create_workstream(db: AsyncSession, name: str, description: str = "") -> WorkstreamResponse:
    """Create a new workstream."""
    ws = WorkstreamDB(name=name, description=description)
    db.add(ws)
    try:
        await db.commit()
        await db.refresh(ws)
    except Exception:
        await db.rollback()
        logger.exception("Failed to create workstream")
        raise
    return _ws_to_response(ws, 0)


async def update_workstream(
    db: AsyncSession,
    workstream_id: UUID,
    name: str | None = None,
    description: str | None = None,
) -> WorkstreamResponse | None:
    """Update a workstream. Returns None if not found."""
    ws = await db.get(WorkstreamDB, workstream_id)
    if ws is None:
        return None
    if name is not None:
        ws.name = name
    if description is not None:
        ws.description = description
    ws.updated_at = func.now()
    try:
        await db.commit()
        await db.refresh(ws)
    except Exception:
        await db.rollback()
        logger.exception("Failed to update workstream id=%s", workstream_id)
        raise
    count = await db.scalar(
        select(func.count()).select_from(Entry).where(Entry.workstream_id == workstream_id)
    )
    return _ws_to_response(ws, int(count or 0))


async def delete_workstream(db: AsyncSession, workstream_id: UUID) -> bool:
    """Delete a workstream. Entries get SET NULL (not cascade-deleted). Returns False if not found."""
    ws = await db.get(WorkstreamDB, workstream_id)
    if ws is None:
        return False
    await db.delete(ws)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception("Failed to delete workstream id=%s", workstream_id)
        raise
    return True


async def get_workstream_stats(
    db: AsyncSession, workstream_id: UUID,
) -> WorkstreamStatsResponse | None:
    """Return entry count and total characters for a workstream."""
    ws = await db.get(WorkstreamDB, workstream_id)
    if ws is None:
        return None
    result = await db.execute(
        select(
            func.count().label("entry_count"),
            func.coalesce(func.sum(func.length(Entry.content)), 0).label("total_characters"),
            func.max(Entry.updated_at).label("last_updated"),
        )
        .select_from(Entry)
        .where(Entry.workstream_id == workstream_id)
    )
    row = result.one()
    return WorkstreamStatsResponse(
        workstream_id=workstream_id,
        entry_count=int(row.entry_count),
        total_characters=int(row.total_characters),
        last_updated=row.last_updated or ws.updated_at,
    )
