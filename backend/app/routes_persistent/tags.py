"""Tag catalog and entry tagging API."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.database import get_db
from app.persistence.schemas import EntryTagsListResponse, TagCreate, TagResponse, TagUpdate, TagsListResponse
from app.persistence.tag_service import (
    EntryNotFoundError,
    EntryTagAlreadyExistsError,
    EntryTagNotFoundError,
    TagAlreadyExistsError,
    TagNotFoundError,
    add_entry_tag,
    create_tag,
    delete_tag,
    list_entry_tags,
    list_tags,
    remove_entry_tag,
    update_tag,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


@router.get("/tags", response_model=TagsListResponse, summary="List all tags")
async def get_tags(db: AsyncSession = Depends(get_db)) -> TagsListResponse:
    try:
        return await list_tags(db)
    except Exception as e:
        logger.exception("Failed to list tags")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list tags") from e


@router.post("/tags", response_model=TagResponse, status_code=status.HTTP_201_CREATED, summary="Create a tag")
async def post_tag(data: TagCreate, db: AsyncSession = Depends(get_db)) -> TagResponse:
    try:
        return await create_tag(db, data)
    except TagAlreadyExistsError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tag already exists") from None
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    except Exception as e:
        logger.exception("Failed to create tag")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create tag") from e


@router.patch("/tags/{tag_id}", response_model=TagResponse, summary="Rename a tag")
async def patch_tag(tag_id: UUID, data: TagUpdate, db: AsyncSession = Depends(get_db)) -> TagResponse:
    try:
        return await update_tag(db, tag_id, data)
    except TagNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found") from None
    except TagAlreadyExistsError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tag name already in use") from None
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    except Exception as e:
        logger.exception("Failed to update tag")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update tag") from e


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a tag")
async def delete_tag_route(tag_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    try:
        await delete_tag(db, tag_id)
    except TagNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found") from None
    except Exception as e:
        logger.exception("Failed to delete tag")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete tag") from e


@router.get("/entries/{entry_id}/tags", response_model=EntryTagsListResponse, summary="List tags on an entry")
async def get_entry_tags(entry_id: UUID, db: AsyncSession = Depends(get_db)) -> EntryTagsListResponse:
    try:
        return await list_entry_tags(db, entry_id)
    except EntryNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found") from None
    except Exception as e:
        logger.exception("Failed to list entry tags")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list entry tags") from e


@router.post(
    "/entries/{entry_id}/tags",
    response_model=TagResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a tag to an entry",
)
async def post_entry_tag(entry_id: UUID, data: TagCreate, db: AsyncSession = Depends(get_db)) -> TagResponse:
    try:
        return await add_entry_tag(db, entry_id, data)
    except EntryNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found") from None
    except EntryTagAlreadyExistsError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Entry is already tagged with this name") from None
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    except Exception as e:
        logger.exception("Failed to assign tag")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to assign tag") from e


@router.delete(
    "/entries/{entry_id}/tags/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a tag from an entry",
)
async def delete_entry_tag(entry_id: UUID, tag_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    try:
        await remove_entry_tag(db, entry_id, tag_id)
    except EntryTagNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not on entry") from None
    except Exception as e:
        logger.exception("Failed to remove entry tag")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to remove entry tag") from e
