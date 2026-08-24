"""Focused tests for governed Knowledge Resolver V1."""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID

import pytest

from app.persistence.models import ComponentName, Entry, EntryStatus, EntryType
from app.schemas.context_assembly import (
    RepositoryAnalysisInput,
    RepositoryFileInput,
    RequirementAnalysisInput,
)
from app.services import knowledge_resolver as resolver

WORKSTREAM_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")


def _entry(
    entry_id: str,
    title: str,
    content: str,
    *,
    workstream_id: UUID | None,
    status: EntryStatus = EntryStatus.RESOLVED,
) -> Entry:
    return Entry(
        id=UUID(entry_id),
        title=title,
        content=content,
        source="test://knowledge",
        author="qa",
        status=status,
        entry_type=EntryType.DOCUMENTATION,
        component_name=ComponentName.UNKNOWN,
        workstream_id=workstream_id,
        created_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 8, 20, tzinfo=timezone.utc),
    )


class _Rows:
    def __init__(self, entries: list[Entry]) -> None:
        self.entries = entries

    def scalars(self) -> "_Rows":
        return self

    def all(self) -> list[Entry]:
        return list(self.entries)


class _DB:
    def __init__(self, entries: list[Entry]) -> None:
        self.entries = entries

    async def execute(self, _statement: object) -> _Rows:
        # Resolver rechecks lifecycle/scope after the SQL query, so returning
        # the complete fixture set exercises the defence-in-depth guard.
        return _Rows(self.entries)


class _Embedder:
    async def embed_text(self, _text: str) -> list[float]:
        return [0.01] * 1024


@pytest.fixture
def entries() -> list[Entry]:
    return [
        _entry(
            "11111111-1111-4111-8111-111111111111",
            "Protocol Wizard Foundation Architecture",
            "Vue Vite Pinia router MongoDB API modules configuration",
            workstream_id=WORKSTREAM_ID,
        ),
        _entry(
            "22222222-2222-4222-8222-222222222222",
            "Frontend Standards — Project",
            "Vue TypeScript project component engineering conventions",
            workstream_id=None,
        ),
        _entry(
            "33333333-3333-4333-8333-333333333333",
            "Draft frontend experiment",
            "Vue experimental notes",
            workstream_id=None,
            status=EntryStatus.OPEN,
        ),
        _entry(
            "44444444-4444-4444-8444-444444444444",
            "Other project Python standard",
            "Django Python background jobs",
            workstream_id=UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
        ),
    ]


def _requirement() -> RequirementAnalysisInput:
    return RequirementAnalysisInput(
        request_id="JIRA-001",
        title="Foundation",
        description="Build the Vue/Vite foundation with Pinia, router and API layer.",
        acceptance_criteria=["Configure MongoDB", "Create the modules configuration"],
        clarified_requirement="Create the Protocol Wizard application foundation.",
    )


def _repository() -> RepositoryAnalysisInput:
    return RepositoryAnalysisInput(
        name="protocol-wizard",
        commit_sha="abcdef1234567",
        relevant_files=[RepositoryFileInput(path="src/App.vue", language="vue")],
        architecture_context=["Vue 3", "TypeScript", "Pinia"],
    )


@pytest.mark.asyncio
async def test_resolver_combines_workstream_and_shared_approved_knowledge(monkeypatch, entries):
    similarities = {
        "11111111-1111-4111-8111-111111111111": 0.92,
        "22222222-2222-4222-8222-222222222222": 0.88,
        "33333333-3333-4333-8333-333333333333": 0.95,
        "44444444-4444-4444-8444-444444444444": 0.91,
    }

    async def fake_semantic_search(_db, _vector, *, workstream_id=None, unassigned=False, **_kwargs):
        eligible = []
        for entry in entries:
            if unassigned and entry.workstream_id is None:
                eligible.append(entry)
            elif workstream_id is not None and entry.workstream_id == workstream_id:
                eligible.append(entry)
        return SimpleNamespace(
            results=[SimpleNamespace(id=e.id, similarity=similarities[str(e.id)]) for e in eligible]
        )

    monkeypatch.setattr(resolver, "semantic_search", fake_semantic_search)
    result = await resolver.resolve_knowledge(
        _DB(entries),
        _Embedder(),
        requirement=_requirement(),
        repository=_repository(),
        workstream_id=WORKSTREAM_ID,
        include_shared=True,
        max_entries=10,
    )

    selected = {item.entry_id for item in result.selected}
    assert "11111111-1111-4111-8111-111111111111" in selected
    assert "22222222-2222-4222-8222-222222222222" in selected
    assert "33333333-3333-4333-8333-333333333333" not in selected  # not resolved
    assert "44444444-4444-4444-8444-444444444444" not in selected  # other workstream
    assert result.resolution_hash.startswith("sha256:")
    assert all(item.reason for item in result.selected)


@pytest.mark.asyncio
async def test_resolver_is_deterministic_for_same_inputs(monkeypatch, entries):
    async def fake_semantic_search(_db, _vector, *, workstream_id=None, unassigned=False, **_kwargs):
        eligible = [
            e for e in entries
            if e.status == EntryStatus.RESOLVED
            and ((unassigned and e.workstream_id is None) or (workstream_id and e.workstream_id == workstream_id))
        ]
        return SimpleNamespace(results=[SimpleNamespace(id=e.id, similarity=0.8) for e in eligible])

    monkeypatch.setattr(resolver, "semantic_search", fake_semantic_search)
    kwargs = dict(
        requirement=_requirement(), repository=_repository(), workstream_id=WORKSTREAM_ID,
        include_shared=True, max_entries=10,
    )
    first = await resolver.resolve_knowledge(_DB(entries), _Embedder(), **kwargs)
    second = await resolver.resolve_knowledge(_DB(entries), _Embedder(), **kwargs)
    assert first.resolution_hash == second.resolution_hash
    assert [i.entry_id for i in first.selected] == [i.entry_id for i in second.selected]


@pytest.mark.asyncio
async def test_resolver_fails_closed_when_embedding_unavailable(entries):
    class BrokenEmbedder:
        async def embed_text(self, _text: str) -> list[float]:
            raise RuntimeError("Bedrock unavailable")

    with pytest.raises(resolver.KnowledgeResolutionUnavailableError):
        await resolver.resolve_knowledge(
            _DB(entries),
            BrokenEmbedder(),
            requirement=_requirement(),
            repository=_repository(),
            workstream_id=WORKSTREAM_ID,
        )

@pytest.mark.asyncio
async def test_resolver_preserves_shared_knowledge_with_scope_budgets(monkeypatch):
    workstream_entries = [
        _entry(
            f"{index:08d}-1111-4111-8111-{index:012d}",
            f"Protocol Wizard Project Knowledge {index}",
            "Vue TypeScript Vite Pinia router API MongoDB foundation",
            workstream_id=WORKSTREAM_ID,
        )
        for index in range(1, 7)
    ]
    shared_entry = _entry(
        "99999999-2222-4222-8222-999999999999",
        "Frontend Standards — Project",
        "Vue TypeScript frontend engineering conventions",
        workstream_id=None,
    )
    all_entries = workstream_entries + [shared_entry]

    similarities = {
        str(entry.id): 0.90 - (idx * 0.01)
        for idx, entry in enumerate(workstream_entries)
    }
    similarities[str(shared_entry.id)] = 0.30

    async def fake_semantic_search(_db, _vector, *, workstream_id=None, unassigned=False, **_kwargs):
        eligible = []
        for entry in all_entries:
            if unassigned and entry.workstream_id is None:
                eligible.append(entry)
            elif workstream_id is not None and entry.workstream_id == workstream_id:
                eligible.append(entry)
        return SimpleNamespace(
            results=[SimpleNamespace(id=e.id, similarity=similarities[str(e.id)]) for e in eligible]
        )

    monkeypatch.setattr(resolver, "semantic_search", fake_semantic_search)
    result = await resolver.resolve_knowledge(
        _DB(all_entries),
        _Embedder(),
        requirement=_requirement(),
        repository=_repository(),
        workstream_id=WORKSTREAM_ID,
        include_shared=True,
        max_entries=12,
    )

    selected_ids = [item.entry_id for item in result.selected]
    selected_workstream = [item for item in result.selected if item.scope == "workstream"]
    selected_shared = [item for item in result.selected if item.scope == "shared"]

    assert len(selected_workstream) == 5
    assert len(selected_shared) == 1
    assert str(shared_entry.id) in selected_ids
    assert str(workstream_entries[-1].id) not in selected_ids
