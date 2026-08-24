"""Semantic search API."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.database import get_db
from app.persistence.embeddings import EmbeddingService, get_embedding_service
from app.persistence.models import ComponentName, EntryPatchStatus, EntryStatus, EntryType
from app.persistence.schemas import SearchResponse
from app.persistence.constants import SEARCH_DEFAULT_LIMIT, SEARCH_MAX_LIMIT
from app.persistence.search_service import semantic_search

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


@router.get(
    "/entries/search",
    response_model=SearchResponse,
    summary="Semantic search across knowledge base entries",
)
async def search_entries(
    q: str = Query(..., description="Natural-language search query"),
    component: ComponentName | None = Query(None, description="Filter by component"),
    entry_type: EntryType | None = Query(None, alias="type", description="Filter by entry type"),
    entry_status: EntryPatchStatus | None = Query(
        None, alias="status", description="Filter by entry status"
    ),
    tag: str | None = Query(None, description="Filter by tag name (case-insensitive)"),
    workstream_id: UUID | None = Query(None, description="Filter by workstream"),
    unassigned: bool = Query(False, description="Show only entries without a workstream"),
    limit: int = Query(
        SEARCH_DEFAULT_LIMIT,
        ge=1,
        le=SEARCH_MAX_LIMIT,
        description=f"Max results (default {SEARCH_DEFAULT_LIMIT}, max {SEARCH_MAX_LIMIT})",
    ),
    db: AsyncSession = Depends(get_db),
    embedder: EmbeddingService = Depends(get_embedding_service),
) -> SearchResponse:
    query_text = q.strip()
    if not query_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[
                {
                    "type": "value_error",
                    "loc": ["query", "q"],
                    "msg": "must not be empty or whitespace-only",
                }
            ],
        )

    try:
        query_vector = await embedder.embed_text(query_text)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[{"type": "value_error", "msg": str(e), "loc": ["query", "q"]}],
        ) from e
    except Exception as e:
        logger.exception("Embedding generation failed for search query")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding generation failed; try again later.",
        ) from e

    try:
        return await semantic_search(
            db,
            query_vector,
            query_text=query_text,
            workstream_id=workstream_id,
            unassigned=unassigned,
            component=component,
            entry_type=entry_type,
            status=EntryStatus(entry_status.value) if entry_status is not None else None,
            tag=tag,
            limit=limit,
        )
    except Exception as e:
        logger.exception("Semantic search failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed",
        ) from e
