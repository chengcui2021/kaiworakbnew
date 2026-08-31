"""Entry creation API."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.persistence.database import get_db
from app.persistence.embeddings import EmbeddingService, get_embedding_service
from app.persistence.constants import EMBEDDING_DIMENSION, LIST_DEFAULT_LIMIT, LIST_MAX_LIMIT
from app.persistence.entries_list_service import list_entries
from app.persistence.entry_response import entry_to_response
from app.persistence.entry_service import delete_entry, update_entry
from app.persistence.entry_status_service import EntryNotFoundError, update_entry_status
from app.persistence.models import ComponentName, Entry, EntryPatchStatus, EntryStatus, EntryTag, EntryType
from app.persistence.schemas import EntryCreate, EntryListResponse, EntryResponse, EntryStatusUpdate, EntryUpdate
from app.services.tenant_scope import validate_entry_ownership

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


@router.get(
    "/entries",
    response_model=EntryListResponse,
    summary="List knowledge base entries",
)
async def get_entries(
    component: ComponentName | None = None,
    entry_type: EntryType | None = Query(None, alias="type"),
    entry_status: EntryPatchStatus | None = Query(None, alias="status"),
    tag: str | None = Query(None, description="Filter by tag name (case-insensitive)"),
    workstream_id: UUID | None = Query(None, description="Filter by workstream"),
    unassigned: bool = Query(False, description="Show only entries without a workstream"),
    limit: int = Query(
        LIST_DEFAULT_LIMIT,
        ge=1,
        le=LIST_MAX_LIMIT,
        description=f"Page size (default {LIST_DEFAULT_LIMIT}, max {LIST_MAX_LIMIT})",
    ),
    offset: int = Query(0, ge=0, description="Number of entries to skip"),
    db: AsyncSession = Depends(get_db),
) -> EntryListResponse:
    return await list_entries(
        db,
        workstream_id=workstream_id,
        unassigned=unassigned,
        component=component,
        entry_type=entry_type,
        entry_status=EntryStatus(entry_status.value) if entry_status is not None else None,
        tag=tag,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/entries/{entry_id}",
    response_model=EntryResponse,
    summary="Get a single knowledge base entry",
)
async def get_entry(
    entry_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> EntryResponse:
    result = await db.execute(
        select(Entry)
        .where(Entry.id == entry_id)
        .options(selectinload(Entry.entry_tags).selectinload(EntryTag.tag))
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    return entry_to_response(entry)


@router.put(
    "/entries/{entry_id}",
    response_model=EntryResponse,
    summary="Update a knowledge base entry",
)
async def put_entry(
    entry_id: UUID,
    data: EntryUpdate,
    db: AsyncSession = Depends(get_db),
    embedder: EmbeddingService = Depends(get_embedding_service),
) -> EntryResponse:
    try:
        validate_entry_ownership(data.owner_scope, data.tenant_id, data.workspace_id, data.repository_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    # Fetch existing entry to compare content
    existing = await db.execute(select(Entry).where(Entry.id == entry_id))
    existing_entry = existing.scalar_one_or_none()
    if existing_entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")

    # Only re-generate embedding if content changed
    new_embedding: list[float] | None = None
    if data.content != existing_entry.content:
        try:
            new_embedding = await embedder.embed_text(data.content)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=[{"type": "value_error", "msg": str(e), "loc": ["body", "content"]}],
            ) from e
        except Exception:
            logger.warning("Embedding generation unavailable; entry will be saved without new vector")

        if new_embedding is not None and len(new_embedding) != EMBEDDING_DIMENSION:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Embedding dimension mismatch",
            )

    try:
        return await update_entry(db, entry_id, data, new_embedding)
    except EntryNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found") from None
    except Exception as e:
        logger.exception("Failed to update entry")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update entry",
        ) from e


@router.delete(
    "/entries/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a knowledge base entry",
)
async def delete_entry_endpoint(
    entry_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    try:
        await delete_entry(db, entry_id)
    except EntryNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found") from None
    except Exception as e:
        logger.exception("Failed to delete entry")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete entry",
        ) from e


@router.patch(
    "/entries/{entry_id}",
    response_model=EntryResponse,
    summary="Update entry lifecycle status",
)
async def patch_entry_status(
    entry_id: UUID,
    data: EntryStatusUpdate,
    db: AsyncSession = Depends(get_db),
) -> EntryResponse:
    try:
        return await update_entry_status(db, entry_id, data.status)
    except EntryNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entry not found",
        ) from None
    except Exception as e:
        logger.exception("Failed to update entry status")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update entry status",
        ) from e


@router.post(
    "/entries",
    response_model=EntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a knowledge base entry",
)
async def create_entry(
    data: EntryCreate,
    db: AsyncSession = Depends(get_db),
    embedder: EmbeddingService = Depends(get_embedding_service),
) -> EntryResponse:
    try:
        validate_entry_ownership(data.owner_scope, data.tenant_id, data.workspace_id, data.repository_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    vector: list[float] | None = None
    try:
        vector = await embedder.embed_text(data.content)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[{"type": "value_error", "msg": str(e), "loc": ["body", "content"]}],
        ) from e
    except Exception:
        logger.warning("Embedding generation unavailable; entry will be saved without vector")

    if vector is not None and len(vector) != EMBEDDING_DIMENSION:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Embedding dimension mismatch",
        )

    entry = Entry(
        entry_type=data.entry_type,
        component_name=data.component_name,
        title=data.title,
        content=data.content,
        source=data.source,
        author=data.author,
        status=data.status or EntryStatus.OPEN,
        embedding=vector,
        workstream_id=data.workstream_id,
        owner_scope=data.owner_scope,
        tenant_id=data.tenant_id,
        workspace_id=data.workspace_id,
        repository_id=data.repository_id,
        knowledge_kind=data.knowledge_kind,
        applies_to=data.applies_to,
        priority=data.priority,
    )
    db.add(entry)
    try:
        await db.commit()
        await db.refresh(entry)
    except Exception as e:
        await db.rollback()
        logger.exception("Failed to persist entry")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save entry",
        ) from e

    return EntryResponse.model_validate(entry)
