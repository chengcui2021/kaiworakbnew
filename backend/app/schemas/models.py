"""Pydantic schemas for the Knowledge Base workspace domain."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class Workspace(BaseModel):
    id: str
    name: str
    description: str = ""
    created_at: str
    updated_at: str
    document_count: int = 0


class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = ""


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1)
    description: Optional[str] = None


# ---------------------------------------------------------------------------
# Approval status (Evolution: KB approval workflow)
# ---------------------------------------------------------------------------
APPROVAL_DRAFT = "draft"
APPROVAL_APPROVED = "approved"
APPROVAL_ARCHIVED = "archived"
APPROVAL_STATUSES = {APPROVAL_DRAFT, APPROVAL_APPROVED, APPROVAL_ARCHIVED}


class Document(BaseModel):
    id: str
    workspace_id: str
    title: str
    content: str
    created_at: str
    updated_at: str
    # Knowledge lifecycle: draft -> approved -> archived. New entries are drafts.
    approval_status: str = APPROVAL_DRAFT
    # Set when the entry is approved; cleared if reverted to draft.
    approved_at: Optional[str] = None


class DocumentCreate(BaseModel):
    title: str = Field(..., min_length=1)
    content: str = ""


class DocumentStatusUpdate(BaseModel):
    approval_status: str = Field(..., description="draft | approved | archived")


class WorkspaceStats(BaseModel):
    workspace_id: str
    document_count: int
    total_characters: int
    last_updated: Optional[str] = None


class SearchResultItem(BaseModel):
    document: Document
    snippet: str


class SearchResponse(BaseModel):
    query: str
    workspace_id: str
    total: int
    results: list[SearchResultItem]


class ValidationCheck(BaseModel):
    name: str
    label: str
    status: str  # 'pass' | 'fail' | 'warning'
    message: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


class WorkspaceValidationResult(BaseModel):
    workspace_id: str
    workspace_name: str
    validated_at: str
    overall_status: str  # 'pass' | 'fail' | 'warning'
    checks: list[ValidationCheck]


class WorkstreamValidationResult(BaseModel):
    workstream_id: str
    workstream_name: str
    validated_at: str
    overall_status: str  # 'pass' | 'fail' | 'warning'
    checks: list[ValidationCheck]


# ---------------------------------------------------------------------------
# Workspace Activity / Audit log (Evolution: Activity & Audit Visibility)
# ---------------------------------------------------------------------------

# Supported activity event types.
EVENT_WORKSPACE_CREATED = "workspace_created"
EVENT_WORKSPACE_RENAMED = "workspace_renamed"
EVENT_DOCUMENT_UPLOADED = "document_uploaded"
EVENT_DOCUMENT_DELETED = "document_deleted"
EVENT_DOCUMENT_MOVED = "document_moved"
# Approval / packaging events (Evolution: Approved Knowledge & Context Packages)
EVENT_DOCUMENT_APPROVED = "document_approved"
EVENT_DOCUMENT_ARCHIVED = "document_archived"
EVENT_DOCUMENT_DRAFTED = "document_drafted"
EVENT_PACKAGE_CREATED = "package_created"


class WorkspaceActivity(BaseModel):
    id: str
    workspace_id: str
    event_type: str  # one of the EVENT_* constants above
    timestamp: str  # ISO 8601
    description: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class MoveDocumentRequest(BaseModel):
    target_workspace_id: str = Field(..., min_length=1)


# ---------------------------------------------------------------------------
# Context Packages (Evolution: cryptographically-verifiable context packaging)
# ---------------------------------------------------------------------------


class ContextPackage(BaseModel):
    id: str
    name: str
    workspace_id: str
    selected_entry_ids: list[str] = Field(default_factory=list)
    created_at: str
    approval_status: str  # 'approved' when every selected entry is approved
    context_hash: str  # 'sha256:<hex>' deterministic integrity hash
    # Convenience metadata for the UI (titles of the bundled entries).
    entry_titles: list[str] = Field(default_factory=list)


class ContextPackageCreate(BaseModel):
    name: str = Field(..., min_length=1)
    selected_entry_ids: list[str] = Field(..., min_length=1)
