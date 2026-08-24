"""Document routes -- all access is scoped to a single workspace."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.schemas.models import (
    APPROVAL_STATUSES,
    Document,
    DocumentCreate,
    DocumentStatusUpdate,
    MoveDocumentRequest,
)
from app.services.store import store

router = APIRouter(prefix="/api/workspaces/{workspace_id}/documents", tags=["documents"])


def _require_workspace(workspace_id: str) -> None:
    if store.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail=f"Workspace '{workspace_id}' not found")


@router.get("", response_model=list[Document])
def list_documents(
    workspace_id: str,
    approval_status: str = Query(
        "", description="Optional filter: draft | approved | archived"),
) -> list[Document]:
    _require_workspace(workspace_id)
    status = approval_status.strip() or None
    if status and status not in APPROVAL_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid approval_status '{status}'")
    return store.list_documents(workspace_id, approval_status=status)


@router.put("/{document_id}/status", response_model=Document)
def update_document_status(
    workspace_id: str, document_id: str, payload: DocumentStatusUpdate,
) -> Document:
    """Change a KB entry's approval status (draft / approved / archived)."""
    _require_workspace(workspace_id)
    try:
        doc = store.set_document_status(workspace_id, document_id, payload.approval_status)
    except ValueError:
        raise HTTPException(status_code=400,
                            detail=f"Invalid approval_status '{payload.approval_status}'")
    if doc is None:
        raise HTTPException(status_code=404,
                            detail=f"Document '{document_id}' not found in workspace '{workspace_id}'")
    return doc


@router.post("", response_model=Document, status_code=201)
def create_document(workspace_id: str, payload: DocumentCreate) -> Document:
    _require_workspace(workspace_id)
    return store.create_document(workspace_id, payload.title, payload.content)


@router.delete("/{document_id}")
def delete_document(workspace_id: str, document_id: str) -> dict:
    _require_workspace(workspace_id)
    if not store.delete_document(workspace_id, document_id):
        raise HTTPException(status_code=404,
                            detail=f"Document '{document_id}' not found in workspace '{workspace_id}'")
    return {"id": document_id, "deleted": True}


@router.post("/{document_id}/move", response_model=Document)
def move_document(workspace_id: str, document_id: str, payload: MoveDocumentRequest) -> Document:
    _require_workspace(workspace_id)
    if payload.target_workspace_id == workspace_id:
        raise HTTPException(status_code=400, detail="Target workspace must differ from the source.")
    try:
        doc = store.move_document(workspace_id, document_id, payload.target_workspace_id)
    except KeyError:
        raise HTTPException(status_code=404,
                            detail=f"Target workspace '{payload.target_workspace_id}' not found")
    if doc is None:
        raise HTTPException(status_code=404,
                            detail=f"Document '{document_id}' not found in workspace '{workspace_id}'")
    return doc
