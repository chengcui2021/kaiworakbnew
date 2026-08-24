"""Workspace CRUD, statistics and validation routes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.schemas.models import (
    Workspace,
    WorkspaceActivity,
    WorkspaceCreate,
    WorkspaceStats,
    WorkspaceUpdate,
    WorkspaceValidationResult,
)
from app.services.store import store
from app.services.workspace_validation import validate_workspace

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


@router.get("", response_model=list[Workspace])
def list_workspaces() -> list[Workspace]:
    return store.list_workspaces()


@router.post("", response_model=Workspace, status_code=201)
def create_workspace(payload: WorkspaceCreate) -> Workspace:
    return store.create_workspace(payload.name, payload.description)


@router.get("/{workspace_id}", response_model=Workspace)
def get_workspace(workspace_id: str) -> Workspace:
    ws = store.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail=f"Workspace '{workspace_id}' not found")
    return ws


@router.put("/{workspace_id}", response_model=Workspace)
def update_workspace(workspace_id: str, payload: WorkspaceUpdate) -> Workspace:
    ws = store.update_workspace(workspace_id, payload.name, payload.description)
    if ws is None:
        raise HTTPException(status_code=404, detail=f"Workspace '{workspace_id}' not found")
    return ws


@router.delete("/{workspace_id}")
def delete_workspace(workspace_id: str) -> dict:
    if not store.delete_workspace(workspace_id):
        raise HTTPException(status_code=404, detail=f"Workspace '{workspace_id}' not found")
    return {"id": workspace_id, "deleted": True}


@router.get("/{workspace_id}/stats", response_model=WorkspaceStats)
def get_workspace_stats(workspace_id: str) -> WorkspaceStats:
    ws = store.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail=f"Workspace '{workspace_id}' not found")
    docs = store.list_documents(workspace_id)
    total_chars = sum(len(d.content) for d in docs)
    last_updated = max((d.updated_at for d in docs), default=ws.updated_at)
    return WorkspaceStats(
        workspace_id=workspace_id,
        document_count=len(docs),
        total_characters=total_chars,
        last_updated=last_updated,
    )


@router.get("/{workspace_id}/validate", response_model=WorkspaceValidationResult)
def validate(workspace_id: str) -> WorkspaceValidationResult:
    try:
        return validate_workspace(store, workspace_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Workspace '{workspace_id}' not found")


@router.get("/{workspace_id}/activities", response_model=list[WorkspaceActivity])
def list_activities(
    workspace_id: str,
    limit: int = Query(20, ge=1, le=100, description="Max number of activities (default 20)"),
) -> list[WorkspaceActivity]:
    """Latest activities for a workspace, newest-first, scoped to this workspace."""
    if store.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail=f"Workspace '{workspace_id}' not found")
    return store.list_activities(workspace_id, limit=limit)
