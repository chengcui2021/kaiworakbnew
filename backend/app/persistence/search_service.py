"""Semantic search over entry embeddings (pgvector cosine distance)."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.persistence.constants import SEARCH_DEFAULT_LIMIT
from app.persistence.entry_response import entry_to_response
from app.persistence.models import ComponentName, Entry, EntryStatus, EntryTag, EntryType, Tag
from app.persistence.schemas import SearchResponse, SearchResultItem
from app.persistence.tag_service import normalize_tag_name
from app.services.tenant_scope import entry_scope_predicate

logger = logging.getLogger(__name__)


async def semantic_search(
    db: AsyncSession,
    query_vector: list[float],
    *,
    query_text: str,
    workstream_id: "UUID | None" = None,
    unassigned: bool = False,
    component: ComponentName | None = None,
    entry_type: EntryType | None = None,
    status: EntryStatus | None = None,
    tag: str | None = None,
    tenant_id: str = "",
    workspace_id: str = "",
    repository_id: str = "",
    enforce_tenant_scope: bool = False,
    limit: int = SEARCH_DEFAULT_LIMIT,
) -> SearchResponse:
    """Rank entries by cosine similarity to ``query_vector`` (normalized embeddings)."""
    tag_name = normalize_tag_name(tag) if tag and tag.strip() else None
    distance = Entry.embedding.cosine_distance(query_vector)
    similarity_expr = (1 - distance).label("similarity")

    stmt: Select = (
        select(Entry, similarity_expr)
        .options(selectinload(Entry.entry_tags).selectinload(EntryTag.tag))
        .where(Entry.embedding.is_not(None))
        .order_by(distance)
        .limit(limit)
    )

    if enforce_tenant_scope:
        stmt = stmt.where(entry_scope_predicate(tenant_id=tenant_id, workspace_id=workspace_id, repository_id=repository_id))

    if unassigned:
        stmt = stmt.where(Entry.workstream_id.is_(None))
    elif workstream_id is not None:
        stmt = stmt.where(Entry.workstream_id == workstream_id)
    if component is not None:
        stmt = stmt.where(Entry.component_name == component)
    if entry_type is not None:
        stmt = stmt.where(Entry.entry_type == entry_type)
    if status is not None:
        stmt = stmt.where(Entry.status == status)
    if tag_name is not None:
        stmt = stmt.join(Entry.entry_tags).join(EntryTag.tag).where(Tag.name == tag_name)

    try:
        rows = (await db.execute(stmt)).unique().all()
    except Exception:
        logger.exception("Semantic search query failed")
        raise

    results: list[SearchResultItem] = []
    for entry, sim in rows:
        base = entry_to_response(entry)
        results.append(
            SearchResultItem(
                id=base.id,
                entry_type=base.entry_type,
                component_name=base.component_name,
                title=base.title,
                content=base.content,
                source=base.source,
                author=base.author,
                status=base.status,
                created_at=base.created_at,
                updated_at=base.updated_at,
                workstream_id=base.workstream_id,
                tags=base.tags,
                similarity=float(sim),
            )
        )

    return SearchResponse(query=query_text, results=results, count=len(results))
