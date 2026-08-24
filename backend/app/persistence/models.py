"""SQLAlchemy ORM models for the metamorphic knowledge base."""

from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.persistence.constants import EMBEDDING_DIMENSION, ENTRY_TITLE_MAX_LENGTH
from app.persistence.db_types import AsyncPgVector


class EntryType(str, enum.Enum):
    """Classification of a knowledge entry."""

    DOCUMENTATION = "documentation"
    REQUIREMENT = "requirement"
    CONSTRAINT = "constraint"
    EXAMPLE = "example"
    OTHER = "other"


class ComponentName(str, enum.Enum):
    """Subsystem or area this entry relates to."""

    INGESTION = "ingestion"
    STORAGE = "storage"
    RETRIEVAL = "retrieval"
    EMBEDDING = "embedding"
    API = "api"
    ADMIN = "admin"
    UNKNOWN = "unknown"


class EntryStatus(str, enum.Enum):
    """Lifecycle state of an entry (stored in PostgreSQL ``entry_status``)."""

    OPEN = "open"
    RESOLVED = "resolved"
    DEFERRED = "deferred"
    SUPERSEDED = "superseded"
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    REJECTED = "rejected"


class EntryPatchStatus(str, enum.Enum):
    """Allowed values for PATCH /entries/{id} status updates."""

    OPEN = "open"
    RESOLVED = "resolved"
    DEFERRED = "deferred"
    SUPERSEDED = "superseded"


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    return [m.value for m in enum_cls]


class Base(DeclarativeBase):
    """Base class for ORM models."""


class WorkstreamDB(Base):
    """Persistent workstream stored in PostgreSQL."""

    __tablename__ = "workstreams"
    __table_args__ = (Index("ix_workstreams_name", "name", unique=True),)

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text(), server_default=text("''"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    entries: Mapped[list["Entry"]] = relationship(back_populates="workstream")

    def __repr__(self) -> str:
        return f"WorkstreamDB(id={self.id!r}, name={self.name!r})"


class Entry(Base):
    """Semantic knowledge entry stored in PostgreSQL with pgvector."""

    __tablename__ = "entries"

    __table_args__ = (
        Index("ix_entries_entry_type", "type"),
        Index("ix_entries_component", "component"),
        Index("ix_entries_status", "status"),
        Index("ix_entries_created_at", "created_at"),
        Index("ix_entries_workstream_id", "workstream_id"),
        Index(
            "ix_entries_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    entry_type: Mapped[EntryType] = mapped_column(
        "type",
        SQLEnum(
            EntryType,
            name="entry_type",
            native_enum=True,
            values_callable=_enum_values,
            create_type=False,
        ),
        nullable=False,
    )

    component_name: Mapped[ComponentName] = mapped_column(
        "component",
        SQLEnum(
            ComponentName,
            name="component_name",
            native_enum=True,
            values_callable=_enum_values,
            create_type=False,
        ),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(Text(), nullable=False)
    title: Mapped[str] = mapped_column(String(ENTRY_TITLE_MAX_LENGTH), nullable=False)
    source: Mapped[str | None] = mapped_column(Text(), nullable=True)
    author: Mapped[str] = mapped_column(String(255), nullable=False)

    status: Mapped[EntryStatus] = mapped_column(
        SQLEnum(
            EntryStatus,
            name="entry_status",
            native_enum=True,
            values_callable=_enum_values,
            create_type=False,
        ),
        nullable=False,
    )

    embedding: Mapped[list[float] | None] = mapped_column(
        AsyncPgVector(EMBEDDING_DIMENSION),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    workstream_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workstreams.id", ondelete="SET NULL"),
        nullable=True,
    )

    workstream: Mapped["WorkstreamDB | None"] = relationship(back_populates="entries")

    jira_links: Mapped[list["EntryJiraLink"]] = relationship(
        back_populates="entry",
        cascade="all, delete-orphan",
        order_by="EntryJiraLink.created_at",
    )

    entry_tags: Mapped[list["EntryTag"]] = relationship(
        back_populates="entry",
        cascade="all, delete-orphan",
        order_by="EntryTag.created_at",
    )

    def __repr__(self) -> str:
        return f"Entry(id={self.id!r}, entry_type={self.entry_type!r}, status={self.status!r})"


class EntryJiraLink(Base):
    """Association between a KB entry and a Jira issue key."""

    __tablename__ = "entry_jira_links"
    __table_args__ = (
        UniqueConstraint("entry_id", "jira_key", name="uq_entry_jira_links_entry_key"),
        Index("ix_entry_jira_links_jira_key", "jira_key"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    entry_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("entries.id", ondelete="CASCADE"),
        nullable=False,
    )
    jira_key: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    entry: Mapped[Entry] = relationship(back_populates="jira_links")

    def __repr__(self) -> str:
        return f"EntryJiraLink(entry_id={self.entry_id!r}, jira_key={self.jira_key!r})"


class Tag(Base):
    """Reusable label assignable to many KB entries."""

    __tablename__ = "tags"
    __table_args__ = (Index("ix_tags_name", "name", unique=True),)

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    entry_tags: Mapped[list["EntryTag"]] = relationship(
        back_populates="tag",
        cascade="all, delete-orphan",
    )


class Template(Base):
    """Reusable document template stored as markdown."""

    __tablename__ = "templates"
    __table_args__ = (Index("ix_templates_name", "name", unique=True),)

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class EntryTag(Base):
    """Association between a KB entry and a tag."""

    __tablename__ = "entry_tags"
    __table_args__ = (
        UniqueConstraint("entry_id", "tag_id", name="uq_entry_tags_entry_tag"),
        Index("ix_entry_tags_tag_id", "tag_id"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    entry_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("entries.id", ondelete="CASCADE"),
        nullable=False,
    )
    tag_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tags.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    entry: Mapped[Entry] = relationship(back_populates="entry_tags")
    tag: Mapped[Tag] = relationship(back_populates="entry_tags")


class LLMUsage(Base):
    """Record of a single LLM API call with token counts."""

    __tablename__ = "llm_usage"
    __table_args__ = (Index("ix_llm_usage_created_at", "created_at"),)

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    route: Mapped[str] = mapped_column(String(255), nullable=False)
    model_id: Mapped[str] = mapped_column(String(255), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer(), nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class ContextAssemblyLockDB(Base):
    """Persisted governed Context Assembly Lock and the request that produced it."""

    __tablename__ = "context_assembly_locks"

    lock_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    context_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    lock_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    assembly_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    request_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
