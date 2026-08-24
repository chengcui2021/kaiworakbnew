"""Shared Knowledge Context Assembly primitives.

Context Packages (``app.routes.packages``) and Governed Context Assembly
(``app.services.context_assembly``) both select approved persistent KB
knowledge and hash it. Both go through the helpers below so the knowledge
base has exactly one knowledge-selection / hashing mechanism rather than a
parallel one per feature.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.models import Entry, EntryStatus

# In the PostgreSQL-backed KB console, lifecycle status 'resolved' is the
# approved / production-ready equivalent used for context selection.
APPROVED_ENTRY_STATUS = EntryStatus.RESOLVED


class UnknownEntryIdsError(Exception):
    """Raised when selected entry ids are malformed or absent from the KB."""

    def __init__(self, entry_ids: list[str]) -> None:
        self.entry_ids = entry_ids
        super().__init__(f"Entries not found: {entry_ids}")


class UnapprovedEntryError(Exception):
    """Raised when selected entries are not approved knowledge."""

    def __init__(self, entry_ids: list[str]) -> None:
        self.entry_ids = entry_ids
        super().__init__(f"Entries not approved/resolved: {entry_ids}")


def canonical_json(payload: Any) -> str:
    """Canonical JSON: sorted keys, no insignificant whitespace, UTF-8 safe."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_digest(payload: Any) -> str:
    """``sha256:<hex>`` over the canonical JSON form of ``payload``."""
    digest = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def compute_entry_context_hash(entries: Sequence[Entry]) -> str:
    """Deterministic hash over persistent KB entries.

    Entries are sorted by id and reduced to ``{id, content}`` so selection
    ordering is irrelevant and any consumer can recompute the hash.
    """
    payload = [
        {"id": str(e.id), "content": e.content}
        for e in sorted(entries, key=lambda item: str(item.id))
    ]
    return sha256_digest(payload)


async def select_approved_entries(
    db: AsyncSession, raw_entry_ids: Sequence[str],
) -> list[Entry]:
    """Load persistent KB entries, enforcing the approved-knowledge constraint.

    Returns the entries in the order they were requested. Raises
    :class:`UnknownEntryIdsError` for malformed or missing ids and
    :class:`UnapprovedEntryError` when any entry is not approved, so
    unapproved knowledge can never silently enter an assembled context.
    """
    entry_ids: list[UUID] = []
    invalid_ids: list[str] = []
    for raw_id in raw_entry_ids:
        try:
            entry_ids.append(UUID(str(raw_id)))
        except ValueError:
            invalid_ids.append(str(raw_id))
    if invalid_ids:
        raise UnknownEntryIdsError(invalid_ids)
    if not entry_ids:
        return []

    result = await db.execute(select(Entry).where(Entry.id.in_(entry_ids)))
    by_id = {str(e.id): e for e in result.scalars().all()}
    missing = [str(eid) for eid in entry_ids if str(eid) not in by_id]
    if missing:
        raise UnknownEntryIdsError(missing)

    entries = [by_id[str(eid)] for eid in entry_ids]
    not_approved = [str(e.id) for e in entries if e.status != APPROVED_ENTRY_STATUS]
    if not_approved:
        raise UnapprovedEntryError(not_approved)
    return entries
