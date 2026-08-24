"""Workstream CRUD, statistics and validation routes (PostgreSQL-backed)."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.database import get_db
from app.persistence.entries_list_service import list_entries
from app.persistence.schemas import (
    EntryResponse,
    WorkstreamCreate,
    WorkstreamResponse,
    WorkstreamStatsResponse,
    WorkstreamUpdate,
)
from app.persistence.workstream_service import (
    create_workstream,
    delete_workstream,
    get_workstream,
    get_workstream_stats,
    list_workstreams,
    update_workstream,
)
from app.schemas.models import WorkstreamValidationResult
from app.services.workstream_validation import validate_workstream

router = APIRouter(prefix="/api/workstreams", tags=["workstreams"])


@router.get("", response_model=list[WorkstreamResponse])
async def list_workstreams_endpoint(
    db: AsyncSession = Depends(get_db),
) -> list[WorkstreamResponse]:
    return await list_workstreams(db)


@router.post("", response_model=WorkstreamResponse, status_code=201)
async def create_workstream_endpoint(
    payload: WorkstreamCreate,
    db: AsyncSession = Depends(get_db),
) -> WorkstreamResponse:
    return await create_workstream(db, payload.name, payload.description)


@router.get("/{workstream_id}", response_model=WorkstreamResponse)
async def get_workstream_endpoint(
    workstream_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> WorkstreamResponse:
    ws = await get_workstream(db, workstream_id)
    if ws is None:
        raise HTTPException(status_code=404, detail=f"Workstream '{workstream_id}' not found")
    return ws


@router.put("/{workstream_id}", response_model=WorkstreamResponse)
async def update_workstream_endpoint(
    workstream_id: UUID,
    payload: WorkstreamUpdate,
    db: AsyncSession = Depends(get_db),
) -> WorkstreamResponse:
    ws = await update_workstream(db, workstream_id, payload.name, payload.description)
    if ws is None:
        raise HTTPException(status_code=404, detail=f"Workstream '{workstream_id}' not found")
    return ws


@router.delete("/{workstream_id}")
async def delete_workstream_endpoint(
    workstream_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not await delete_workstream(db, workstream_id):
        raise HTTPException(status_code=404, detail=f"Workstream '{workstream_id}' not found")
    return {"id": str(workstream_id), "deleted": True}


@router.get("/{workstream_id}/stats", response_model=WorkstreamStatsResponse)
async def get_workstream_stats_endpoint(
    workstream_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> WorkstreamStatsResponse:
    stats = await get_workstream_stats(db, workstream_id)
    if stats is None:
        raise HTTPException(status_code=404, detail=f"Workstream '{workstream_id}' not found")
    return stats


@router.get("/{workstream_id}/validate", response_model=WorkstreamValidationResult)
async def validate_workstream_endpoint(
    workstream_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> WorkstreamValidationResult:
    try:
        return await validate_workstream(db, workstream_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Workstream '{workstream_id}' not found")


@router.get("/{workstream_id}/entries", response_model=list[EntryResponse])
async def list_workstream_entries(
    workstream_id: UUID,
    limit: int = Query(20, ge=1, le=100, description="Max entries (default 20)"),
    db: AsyncSession = Depends(get_db),
) -> list[EntryResponse]:
    """Recent entries belonging to this workstream, newest-first."""
    ws = await get_workstream(db, workstream_id)
    if ws is None:
        raise HTTPException(status_code=404, detail=f"Workstream '{workstream_id}' not found")
    result = await list_entries(db, workstream_id=workstream_id, limit=limit)
    return result.entries
