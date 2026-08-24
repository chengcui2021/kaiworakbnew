"""Governed automatic knowledge resolution for Context Assembly.

Resolver V1 intentionally composes existing KB capabilities rather than
introducing a parallel knowledge store or a second governance authority:

* only lifecycle ``resolved`` entries are eligible;
* retrieval is scoped to the requested workstream plus optional shared
  (unassigned) approved knowledge;
* Bedrock/pgvector semantic retrieval is combined with deterministic lexical
  relevance over the same approved scopes;
* results are ranked and hashed deterministically, with selection reasons;
* the existing ``select_approved_entries`` gate still re-validates every
  selected id before Context Assembly freezes content snapshots.
"""
from __future__ import annotations

import re
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.constants import SEARCH_MAX_LIMIT
from app.persistence.embeddings import EmbeddingService
from app.persistence.models import Entry, EntryStatus
from app.persistence.search_service import semantic_search
from app.schemas.context_assembly import (
    KnowledgeResolution,
    RepositoryAnalysisInput,
    RequirementAnalysisInput,
    ResolvedKnowledgeItem,
)
from app.services.knowledge_context import sha256_digest

RESOLVER_VERSION = "1"
_LEXICAL_ENTRY_LIMIT = 100
_WORKSTREAM_SELECTION_LIMIT = 5
_SHARED_SELECTION_LIMIT = 3
_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_./:+-]*")
_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "using",
    "must", "should", "will", "are", "is", "be", "to", "of", "in", "on",
    "a", "an", "or", "as", "at", "by", "it", "its", "no", "not",
}


class KnowledgeResolutionError(Exception):
    """Base class for fail-closed knowledge-resolution failures."""


class KnowledgeResolutionUnavailableError(KnowledgeResolutionError):
    """Raised when embeddings/search required for automatic resolution fail."""


def build_resolution_query(
    requirement: RequirementAnalysisInput,
    repository: RepositoryAnalysisInput,
) -> str:
    """Build the canonical retrieval query from governed analysis outputs."""
    parts: list[str] = []

    def add(value: str | None) -> None:
        text = " ".join((value or "").split())
        if text and text not in parts:
            parts.append(text)

    add(requirement.title)
    add(requirement.clarified_requirement)
    add(requirement.description)
    for values in (
        requirement.acceptance_criteria,
        requirement.constraints,
        requirement.dependencies,
        repository.impacted_components,
        repository.dependencies,
        repository.architecture_context,
    ):
        for value in values:
            add(value)
    for file in repository.relevant_files:
        add(file.path)
        add(file.language)
        add(file.role)
    return "\n".join(parts)


def _query_tokens(query: str) -> list[str]:
    tokens: list[str] = []
    seen: set[str] = set()
    for raw in _TOKEN_RE.findall(query.casefold()):
        token = raw.strip("._/:-+")
        if len(token) < 3 or token in _STOPWORDS or token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens[:80]


def _lexical_score(entry: Entry, tokens: Sequence[str]) -> float:
    if not tokens:
        return 0.0
    title = (entry.title or "").casefold()
    source = (entry.source or "").casefold()
    content = (entry.content or "").casefold()
    matched_weight = 0.0
    possible = min(len(tokens), 24) * 3.0
    for token in tokens[:24]:
        if token in title:
            matched_weight += 3.0
        elif token in source:
            matched_weight += 2.0
        elif token in content:
            matched_weight += 1.0
    return min(1.0, matched_weight / possible) if possible else 0.0


async def _load_approved_scope_entries(
    db: AsyncSession,
    *,
    workstream_id: UUID | None,
    shared: bool,
) -> list[Entry]:
    stmt = select(Entry).where(Entry.status == EntryStatus.RESOLVED)
    if shared:
        stmt = stmt.where(Entry.workstream_id.is_(None))
    elif workstream_id is not None:
        stmt = stmt.where(Entry.workstream_id == workstream_id)
    else:
        return []
    stmt = stmt.order_by(Entry.updated_at.desc(), Entry.id).limit(_LEXICAL_ENTRY_LIMIT)
    result = await db.execute(stmt)
    entries = list(result.scalars().all())
    # Recheck eligibility in-process as a defence-in-depth guard. The SQL
    # predicate remains the primary database filter.
    eligible: list[Entry] = []
    for entry in entries:
        if entry.status != EntryStatus.RESOLVED:
            continue
        if shared and entry.workstream_id is not None:
            continue
        if not shared and workstream_id is not None and entry.workstream_id != workstream_id:
            continue
        eligible.append(entry)
    return eligible


async def resolve_knowledge(
    db: AsyncSession,
    embedder: EmbeddingService,
    *,
    requirement: RequirementAnalysisInput,
    repository: RepositoryAnalysisInput,
    workstream_id: UUID | None,
    include_shared: bool = True,
    max_entries: int = 12,
    min_similarity: float = 0.25,
) -> KnowledgeResolution:
    """Resolve applicable approved KB knowledge for one governed analysis.

    The function fails closed when semantic resolution infrastructure is
    unavailable. An empty *successful* result is allowed: it means no approved
    entry in the authorised scopes met the relevance criteria.
    """
    query = build_resolution_query(requirement, repository)
    if workstream_id is None and not include_shared:
        payload = {
            "resolver_version": RESOLVER_VERSION, "mode": "automatic", "query": query,
            "workstream_id": None, "include_shared": False, "selected": [],
        }
        return KnowledgeResolution(**payload, resolution_hash=sha256_digest(payload))

    if not query.strip():
        raise KnowledgeResolutionError("Cannot resolve knowledge from empty analysis context.")

    try:
        query_vector = await embedder.embed_text(query)
    except Exception as exc:  # provider/network failure must not silently remove governance
        raise KnowledgeResolutionUnavailableError(
            "Embedding generation failed during automatic knowledge resolution."
        ) from exc

    semantic_by_id: dict[str, float] = {}
    candidate_limit = min(SEARCH_MAX_LIMIT, max(20, max_entries * 3))
    scopes: list[tuple[str, UUID | None, bool]] = []
    if workstream_id is not None:
        scopes.append(("workstream", workstream_id, False))
    if include_shared:
        scopes.append(("shared", None, True))

    try:
        for _scope_name, scope_workstream, unassigned in scopes:
            response = await semantic_search(
                db,
                query_vector,
                query_text=query,
                workstream_id=scope_workstream,
                unassigned=unassigned,
                status=EntryStatus.RESOLVED,
                limit=candidate_limit,
            )
            for item in response.results:
                key = str(item.id)
                semantic_by_id[key] = max(semantic_by_id.get(key, -1.0), float(item.similarity))

        scope_entries: dict[str, Entry] = {}
        scope_names: dict[str, str] = {}
        if workstream_id is not None:
            for entry in await _load_approved_scope_entries(
                db, workstream_id=workstream_id, shared=False
            ):
                scope_entries[str(entry.id)] = entry
                scope_names[str(entry.id)] = "workstream"
        if include_shared:
            for entry in await _load_approved_scope_entries(db, workstream_id=None, shared=True):
                scope_entries[str(entry.id)] = entry
                scope_names.setdefault(str(entry.id), "shared")
    except Exception as exc:
        raise KnowledgeResolutionUnavailableError(
            "KB search failed during automatic knowledge resolution."
        ) from exc

    tokens = _query_tokens(query)
    ranked: list[tuple[float, str, ResolvedKnowledgeItem]] = []
    for entry_id, entry in scope_entries.items():
        semantic = semantic_by_id.get(entry_id)
        lexical = _lexical_score(entry, tokens)
        # Keep strong lexical matches even if vector retrieval did not return
        # the item; otherwise require the configured semantic floor.
        if semantic is None and lexical <= 0.0:
            continue
        if semantic is not None and semantic < min_similarity and lexical <= 0.0:
            continue
        semantic_component = max(0.0, semantic if semantic is not None else 0.0)
        score = round((semantic_component * 0.85) + (lexical * 0.15), 8)
        scope = scope_names.get(entry_id, "shared")
        reason_bits = [
            "approved/resolved",
            "project workstream" if scope == "workstream" else "shared engineering knowledge",
        ]
        if semantic is not None:
            reason_bits.append(f"semantic similarity {semantic:.3f}")
        if lexical > 0:
            reason_bits.append(f"lexical relevance {lexical:.3f}")
        item = ResolvedKnowledgeItem(
            entry_id=entry_id,
            title=entry.title,
            source=entry.source,
            workstream_id=str(entry.workstream_id) if entry.workstream_id else None,
            scope=scope,
            semantic_similarity=round(float(semantic), 8) if semantic is not None else None,
            lexical_score=round(lexical, 8),
            score=score,
            reason="; ".join(reason_bits),
        )
        ranked.append((score, entry_id, item))

    ranked.sort(key=lambda value: (-value[0], value[1]))

    # Preserve both governed knowledge scopes during final selection. A single
    # global top-N can allow a larger project workstream to crowd out shared
    # engineering standards (or vice versa), even when both scopes are
    # explicitly authorised for the run. Resolver V1 therefore applies small,
    # deterministic per-scope budgets before the existing global max_entries
    # cap. This changes only selection precision; eligibility, ranking and the
    # final approved-entry gate remain unchanged.
    workstream_ranked = [row for row in ranked if row[2].scope == "workstream"]
    shared_ranked = [row for row in ranked if row[2].scope == "shared"]
    scoped_ranked = (
        workstream_ranked[:_WORKSTREAM_SELECTION_LIMIT]
        + shared_ranked[:_SHARED_SELECTION_LIMIT]
    )
    scoped_ranked.sort(key=lambda value: (-value[0], value[1]))
    selected = [item for _score, _entry_id, item in scoped_ranked[:max_entries]]
    resolution_payload = {
        "resolver_version": RESOLVER_VERSION,
        "mode": "automatic",
        "query": query,
        "workstream_id": str(workstream_id) if workstream_id else None,
        "include_shared": include_shared,
        "selected": [item.model_dump(mode="json") for item in selected],
    }
    return KnowledgeResolution(
        **resolution_payload,
        resolution_hash=sha256_digest(resolution_payload),
    )
