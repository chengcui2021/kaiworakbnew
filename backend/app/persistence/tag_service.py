"""Tag catalog and entry tagging."""

from __future__ import annotations

import logging
import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.persistence.models import Entry, EntryTag, Tag
from app.persistence.schemas import EntryTagsListResponse, TagCreate, TagResponse, TagUpdate, TagsListResponse

logger = logging.getLogger(__name__)

TAG_NAME_MAX_LENGTH = 64
_TAG_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9 _-]*[a-z0-9]$|^[a-z0-9]$")


class EntryNotFoundError(Exception):
    """Raised when no entry exists for the given id."""


class TagNotFoundError(Exception):
    """Raised when no tag exists for the given id."""


class TagAlreadyExistsError(Exception):
    """Raised when a tag name is already in the catalog."""


class EntryTagAlreadyExistsError(Exception):
    """Raised when an entry is already tagged with the tag."""


class EntryTagNotFoundError(Exception):
    """Raised when an entry is not tagged with the given tag."""


def normalize_tag_name(raw: str) -> str:
    name = re.sub(r"\s+", " ", raw.strip().lower())
    if not name:
        raise ValueError("Tag name must not be empty")
    if len(name) > TAG_NAME_MAX_LENGTH:
        raise ValueError(f"Tag name must be at most {TAG_NAME_MAX_LENGTH} characters")
    if not _TAG_NAME_PATTERN.match(name):
        raise ValueError(
            "Tag name may only contain letters, numbers, spaces, hyphens, and underscores"
        )
    return name


async def _get_tag_by_name(db: AsyncSession, name: str) -> Tag | None:
    result = await db.execute(select(Tag).where(Tag.name == name))
    return result.scalar_one_or_none()


async def list_tags(db: AsyncSession) -> TagsListResponse:
    tags = (await db.execute(select(Tag).order_by(Tag.name.asc()))).scalars().all()
    return TagsListResponse(tags=[TagResponse.model_validate(t) for t in tags], count=len(tags))


async def create_tag(db: AsyncSession, data: TagCreate) -> TagResponse:
    name = normalize_tag_name(data.name)
    if await _get_tag_by_name(db, name) is not None:
        raise TagAlreadyExistsError(name)

    tag = Tag(name=name)
    db.add(tag)
    try:
        await db.commit()
        await db.refresh(tag)
    except Exception:
        await db.rollback()
        logger.exception("Failed to create tag name=%s", name)
        raise
    return TagResponse.model_validate(tag)


async def update_tag(db: AsyncSession, tag_id: UUID, data: TagUpdate) -> TagResponse:
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalar_one_or_none()
    if tag is None:
        raise TagNotFoundError(str(tag_id))

    name = normalize_tag_name(data.name)
    if name != tag.name and await _get_tag_by_name(db, name) is not None:
        raise TagAlreadyExistsError(name)
    tag.name = name

    try:
        await db.commit()
        await db.refresh(tag)
    except Exception:
        await db.rollback()
        logger.exception("Failed to update tag id=%s", tag_id)
        raise
    return TagResponse.model_validate(tag)


async def delete_tag(db: AsyncSession, tag_id: UUID) -> None:
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalar_one_or_none()
    if tag is None:
        raise TagNotFoundError(str(tag_id))

    await db.delete(tag)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception("Failed to delete tag id=%s", tag_id)
        raise


async def list_entry_tags(db: AsyncSession, entry_id: UUID) -> EntryTagsListResponse:
    result = await db.execute(
        select(Entry)
        .where(Entry.id == entry_id)
        .options(selectinload(Entry.entry_tags).selectinload(EntryTag.tag))
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise EntryNotFoundError(str(entry_id))

    tags = [TagResponse.model_validate(et.tag) for et in entry.entry_tags if et.tag is not None]
    return EntryTagsListResponse(entry_id=entry_id, tags=tags, count=len(tags))


async def add_entry_tag(db: AsyncSession, entry_id: UUID, data: TagCreate) -> TagResponse:
    name = normalize_tag_name(data.name)
    result = await db.execute(
        select(Entry)
        .where(Entry.id == entry_id)
        .options(selectinload(Entry.entry_tags))
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise EntryNotFoundError(str(entry_id))

    tag = await _get_tag_by_name(db, name)
    if tag is None:
        tag = Tag(name=name)
        db.add(tag)
        await db.flush()

    if any(et.tag_id == tag.id for et in entry.entry_tags):
        raise EntryTagAlreadyExistsError(name)

    db.add(EntryTag(entry_id=entry_id, tag_id=tag.id))
    try:
        await db.commit()
        await db.refresh(tag)
    except Exception:
        await db.rollback()
        logger.exception("Failed to add tag entry_id=%s name=%s", entry_id, name)
        raise
    return TagResponse.model_validate(tag)


async def remove_entry_tag(db: AsyncSession, entry_id: UUID, tag_id: UUID) -> None:
    result = await db.execute(
        select(EntryTag).where(EntryTag.entry_id == entry_id, EntryTag.tag_id == tag_id)
    )
    link = result.scalar_one_or_none()
    if link is None:
        raise EntryTagNotFoundError(str(tag_id))

    await db.delete(link)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception("Failed to remove tag entry_id=%s tag_id=%s", entry_id, tag_id)
        raise
