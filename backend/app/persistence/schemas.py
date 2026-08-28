"""Pydantic request/response schemas for API payloads."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.persistence.constants import ENTRY_TITLE_MAX_LENGTH
from app.persistence.models import ComponentName, EntryPatchStatus, EntryStatus, EntryType


class WorkstreamCreate(BaseModel):
    """Payload for POST /workstreams."""

    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="", max_length=10_000)


class WorkstreamUpdate(BaseModel):
    """Payload for PUT /workstreams/{id}."""

    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10_000)


class WorkstreamResponse(BaseModel):
    """Workstream returned to clients."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    description: str
    created_at: datetime
    updated_at: datetime
    entry_count: int = Field(default=0, description="Number of entries in this workstream")


class WorkstreamStatsResponse(BaseModel):
    """Statistics for a single workstream."""

    workstream_id: UUID
    entry_count: int = Field(default=0)
    total_characters: int = Field(default=0)
    last_updated: datetime | None = None


class EntryCreate(BaseModel):
    """Payload for POST /entries."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)

    entry_type: EntryType = Field(alias="type", description="Knowledge entry classification")
    component_name: ComponentName = Field(
        alias="component",
        description="Subsystem or component this entry relates to",
    )
    title: str = Field(..., min_length=1, max_length=ENTRY_TITLE_MAX_LENGTH)
    content: str = Field(..., min_length=1, max_length=100_000)
    source: str | None = Field(default=None, max_length=10_000)
    author: str = Field(..., min_length=1, max_length=255)
    status: EntryStatus | None = Field(
        default=None,
        description="Defaults to open when omitted",
    )
    owner_scope: Literal["global", "tenant", "workspace", "repository"] = "global"
    tenant_id: str | None = Field(default=None, max_length=255)
    workspace_id: str | None = Field(default=None, max_length=255)
    repository_id: str | None = Field(default=None, max_length=2000)

    workstream_id: UUID | None = Field(default=None, description="Optional workstream assignment")

    @field_validator("content", "author", "title")
    @classmethod
    def strip_non_empty(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("must not be empty or whitespace-only")
        return s

    @field_validator("source")
    @classmethod
    def source_strip_or_none(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        return s if s else None


class EntryResponse(BaseModel):
    """Created entry returned to clients (embedding stored in DB, not echoed)."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=True,
    )

    id: UUID
    entry_type: EntryType = Field(serialization_alias="type")
    component_name: ComponentName = Field(serialization_alias="component")
    title: str
    content: str
    source: str | None
    author: str
    status: EntryStatus
    owner_scope: str = "global"
    tenant_id: str | None = None
    workspace_id: str | None = None
    repository_id: str | None = None
    created_at: datetime
    updated_at: datetime
    workstream_id: UUID | None = None
    tags: list["TagResponse"] = Field(default_factory=list)


class SearchResultItem(EntryResponse):
    """Entry match with cosine similarity score (1 = identical direction)."""

    similarity: float = Field(..., description="Cosine similarity to the search query (higher is closer)")


class SearchResponse(BaseModel):
    """Semantic search response payload."""

    query: str
    results: list[SearchResultItem]
    count: int


class EntryUpdate(BaseModel):
    """Payload for PUT /entries/{id} — full entry update."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)

    entry_type: EntryType = Field(alias="type", description="Knowledge entry classification")
    component_name: ComponentName = Field(
        alias="component",
        description="Subsystem or component this entry relates to",
    )
    title: str = Field(..., min_length=1, max_length=ENTRY_TITLE_MAX_LENGTH)
    content: str = Field(..., min_length=1, max_length=100_000)
    source: str | None = Field(default=None, max_length=10_000)
    author: str = Field(..., min_length=1, max_length=255)
    status: EntryStatus = Field(..., description="Lifecycle status")
    owner_scope: Literal["global", "tenant", "workspace", "repository"] = "global"
    tenant_id: str | None = Field(default=None, max_length=255)
    workspace_id: str | None = Field(default=None, max_length=255)
    repository_id: str | None = Field(default=None, max_length=2000)

    workstream_id: UUID | None = Field(default=None, description="Optional workstream reassignment")

    @field_validator("content", "author", "title")
    @classmethod
    def strip_non_empty(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("must not be empty or whitespace-only")
        return s

    @field_validator("source")
    @classmethod
    def source_strip_or_none(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        return s if s else None


class EntryStatusUpdate(BaseModel):
    """Payload for PATCH /entries/{id} (status only)."""

    model_config = ConfigDict(extra="forbid")

    status: EntryPatchStatus


class EntryListResponse(BaseModel):
    """Paginated list of knowledge base entries."""

    entries: list[EntryResponse]
    total: int = Field(..., ge=0, description="Total entries matching filters (before pagination)")
    limit: int = Field(..., ge=1)
    offset: int = Field(..., ge=0)


class JiraLinkCreate(BaseModel):
    """Payload for POST /entries/{id}/jira-links."""

    model_config = ConfigDict(extra="forbid")

    jira_key: str = Field(..., min_length=2, max_length=64)


class JiraChildIssueResponse(BaseModel):
    """A story/task linked to an epic."""

    key: str
    title: str
    status: str
    story_points: float | None = None
    browse_url: str


class JiraLinkResponse(BaseModel):
    """Linked Jira issue with optional live metadata."""

    jira_key: str
    title: str | None = None
    status: str | None = None
    issue_type: str | None = None
    story_points: float | None = None
    browse_url: str | None = None
    is_epic: bool = False
    child_issues: list[JiraChildIssueResponse] = Field(default_factory=list)
    enrichment_error: str | None = Field(
        default=None,
        description="Set when the link is stored but Jira metadata could not be loaded",
    )


class JiraLinksListResponse(BaseModel):
    """All Jira links for a KB entry."""

    entry_id: UUID
    links: list[JiraLinkResponse]
    count: int = Field(..., ge=0)


class TagCreate(BaseModel):
    """Payload for creating or assigning a tag by name."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=64)


class TagUpdate(BaseModel):
    """Payload for PATCH /tags/{id}."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=64)


class TagResponse(BaseModel):
    """Tag in the catalog or on an entry."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime


class TagsListResponse(BaseModel):
    """All tags in the catalog."""

    tags: list[TagResponse]
    count: int = Field(..., ge=0)


class EntryTagsListResponse(BaseModel):
    """Tags assigned to a KB entry."""

    entry_id: UUID
    tags: list[TagResponse]
    count: int = Field(..., ge=0)


class TemplateCreate(BaseModel):
    """Payload for POST /templates."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1, max_length=100_000)

    @field_validator("name", "content")
    @classmethod
    def strip_non_empty(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("must not be empty or whitespace-only")
        return s


class TemplateUpdate(BaseModel):
    """Payload for PUT /templates/{id}."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1, max_length=100_000)

    @field_validator("name", "content")
    @classmethod
    def strip_non_empty(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("must not be empty or whitespace-only")
        return s


class TemplateResponse(BaseModel):
    """Template returned to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    content: str
    created_at: datetime
    updated_at: datetime


class TemplatesListResponse(BaseModel):
    """All templates in the catalog."""

    templates: list[TemplateResponse]
    count: int = Field(..., ge=0)
