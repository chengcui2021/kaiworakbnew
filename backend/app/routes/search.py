"""Workspace-scoped search route.

This is the endpoint that previously leaked cross-workspace results.
``workspace_id`` is now REQUIRED and is enforced before any text matching,
so search can only ever return documents from the selected workspace.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from app.schemas.models import SearchResponse, SearchResultItem
from app.services.store import store

logger = logging.getLogger("kb.search")

router = APIRouter(prefix="/api/search", tags=["search"])


def _snippet(content: str, query: str, width: int = 80) -> str:
    if not query:
        return content[:width]
    lowered = content.lower()
    idx = lowered.find(query.lower())
    if idx == -1:
        return content[:width]
    start = max(0, idx - width // 2)
    end = min(len(content), idx + len(query) + width // 2)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(content) else ""
    return f"{prefix}{content[start:end]}{suffix}"


@router.get("", response_model=SearchResponse)
def search(
    workspace_id: str = Query("", description="Active workspace id (required)"),
    q: str = Query("", description="Search query"),
) -> SearchResponse:
    # Enforce workspace context: reject searches without a workspace.
    if not workspace_id or not workspace_id.strip():
        raise HTTPException(status_code=400, detail="workspace_id is required for search")
    if store.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail=f"Workspace '{workspace_id}' not found")

    matches = store.search_documents(workspace_id, q)
    logger.info("search workspace_id=%s query=%r results=%d", workspace_id, q, len(matches))

    results = [
        SearchResultItem(document=doc, snippet=_snippet(doc.content, q))
        for doc in matches
    ]
    return SearchResponse(
        query=q,
        workspace_id=workspace_id,
        total=len(results),
        results=results,
    )
