"""Governed Context Assembly acceptance coverage (MDSU-345, Phase 1).

Each test names the acceptance criterion it provides evidence for. The backend
behaviour already exists (commit "Implement Backend Contract"); what was
missing was any automated assertion of it, which is why AC2-AC8 kept coming
back UNVERIFIED against a CI job that only smoke-tests ``/health``.

These tests describe the shipped contract. They must not be loosened to make a
future change pass — a failure here means the governed-context contract moved.
"""
from __future__ import annotations

import ast
import asyncio
import inspect
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

import _ac9_hash_probe

from app.routes import context_assembly as context_assembly_routes
from app.routes import packages as packages_routes
from app.schemas.context_assembly import (
    ContextAssemblyLock,
    EngineeringGovernanceContext,
    GovernedContextAssembly,
    GovernedInputsRef,
    KnowledgeContext,
    KnowledgeProvenance,
    RepositoryAnalysisContext,
    RepositoryInput,
    RequirementAnalysisContext,
)
from app.services import context_assembly as service
from app.services import knowledge_context
from conftest import (
    APPROVED_ENTRY_ID,
    MISSING_ENTRY_ID,
    SECOND_APPROVED_ENTRY_ID,
    UNAPPROVED_ENTRY_ID,
    StubSession,
    governance_input,
    governed_request,
    make_entry,
    no_repository_mutation,
    repository_input,
    request_input,
)
from app.persistence.models import Entry, EntryStatus


def assemble(client, payload: dict):
    return client.post("/api/governed-context/assemble", json=payload)


def assemble_ok(client, payload: dict) -> dict:
    response = assemble(client, payload)
    assert response.status_code == 200, response.text
    return response.json()


# ---------------------------------------------------------------------------
# AC1 -- Requirement Analysis Context
# ---------------------------------------------------------------------------


def test_ac1_requirement_context_carries_the_original_request(client):
    body = assemble_ok(client, governed_request())
    requirement = body["requirement_context"]

    assert requirement["request_id"] == "MDSU-345"
    assert requirement["title"] == "Add governed context assembly"
    assert requirement["description"].startswith("Combine requirement")
    assert requirement["acceptance_criteria"] == [
        "Deterministic hash",
        "Approved knowledge only",
    ]
    assert requirement["source"] == "jira"
    assert requirement["digest"].startswith("sha256:")


@pytest.mark.parametrize(
    ("field", "value"),
    [("title", "   "), ("description", "\n\t ")],
)
def test_ac1_whitespace_only_request_is_rejected(client, field, value):
    response = assemble(client, governed_request(request=request_input(**{field: value})))

    assert response.status_code == 422
    assert field in response.text


def test_ac1_missing_request_field_is_rejected(client):
    payload = governed_request()
    del payload["request"]["title"]

    assert assemble(client, payload).status_code == 422


# ---------------------------------------------------------------------------
# AC2 -- Repository Analysis Context (structured, read-only)
# ---------------------------------------------------------------------------


def test_ac2_repository_context_is_structured_from_supplied_information(client):
    repository = assemble_ok(client, governed_request())["repository_context"]

    assert repository["name"] == "metamorphic-kb"
    assert repository["branch"] == "main"
    assert repository["commit_sha"] == "abc1234def5678"
    assert repository["file_count"] == 2
    assert repository["languages"] == ["python", "vue"]
    assert repository["top_level_paths"] == ["backend", "frontend"]
    assert [f["path"] for f in repository["files"]] == [
        "backend/app/main.py",
        "frontend/src/App.vue",
    ]
    assert repository["digest"].startswith("sha256:")


def test_ac2_repository_context_emits_every_required_field_with_the_declared_type(client):
    """AC2: the section is *structured* — every governed field is present and typed.

    The value assertions above would still pass if a field were emitted as
    ``None`` or as the wrong JSON type (``file_count`` as a string, ``languages``
    as a comma-joined string), which is exactly the shape drift that stops a
    downstream consumer from reading the contract. This pins the wire types the
    frontend ``RepositoryAnalysisContext`` type declares.
    """
    repository = assemble_ok(client, governed_request())["repository_context"]

    required_types = {
        "read_only": bool,
        "file_count": int,
        "languages": list,
        "top_level_paths": list,
        "digest": str,
    }
    missing = [field for field in required_types if field not in repository]
    assert not missing, f"repository_context is missing required AC2 fields: {missing}"

    for field, expected_type in required_types.items():
        value = repository[field]
        assert value is not None, f"repository_context.{field} must not be null"
        # bool is a subclass of int, so file_count must not be True/False.
        assert isinstance(value, expected_type) and not (
            expected_type is int and isinstance(value, bool)
        ), f"repository_context.{field} is {type(value).__name__}, expected {expected_type.__name__}"

    assert all(isinstance(lang, str) for lang in repository["languages"])
    assert all(isinstance(path, str) for path in repository["top_level_paths"])
    assert repository["file_count"] == len(repository["files"])
    assert repository["digest"].startswith("sha256:")


def test_ac2_repository_context_declares_itself_read_only(client):
    repository = assemble_ok(client, governed_request())["repository_context"]

    assert repository["read_only"] is True
    assert repository["analysis_mode"] == service.REPOSITORY_ANALYSIS_MODE == "read_only_metadata"


def test_ac2_repository_input_contract_accepts_no_local_checkout(client):
    """The contract cannot even express "go look at this working copy".

    Repository analysis is metadata-only, so there is no path/workdir field to
    point at a checkout, and unknown fields are rejected rather than ignored.
    """
    assert set(RepositoryInput.model_fields) == {"name", "url", "branch", "commit_sha", "files"}
    assert RepositoryInput.model_config["extra"] == "forbid"

    response = assemble(
        client, governed_request(repository=repository_input(local_path="/srv/checkout"))
    )
    assert response.status_code == 422


def test_ac2_repository_analysis_never_mutates_the_target_repository():
    """AC2: analysis performs no writes, deletes, or subprocess calls."""
    payload = RepositoryInput(**repository_input())

    with no_repository_mutation():
        context = service.build_repository_context(payload)

    assert context.read_only is True
    assert context.file_count == 2


def test_ac2_full_assembly_performs_no_repository_mutation(client):
    """The guard also holds for the whole four-section assembly, not just AC2."""
    requirement = service.build_requirement_context(
        service.EngineeringRequestInput(**request_input())
    )
    repository = service.build_repository_context(RepositoryInput(**repository_input()))
    knowledge = service.build_knowledge_context([make_entry(APPROVED_ENTRY_ID)])
    governance = service.build_governance_context(
        [service.GovernanceRuleInput(**governance_input())]
    )

    with no_repository_mutation():
        assembly = service.assemble_governed_context(
            requirement, repository, knowledge, governance
        )

    assert assembly.context_hash.startswith("sha256:")


def test_ac2_dot_slash_prefix_is_normalised_without_eating_dotfiles(client):
    """``./x`` normalises to ``x``; ``.github/...`` keeps its leading dot.

    Repository lineage would be wrong if a dotfile directory silently lost its
    dot, so the normalisation must strip the ``./`` prefix, not the characters.
    """
    repository = assemble_ok(
        client,
        governed_request(
            repository=repository_input(
                files=[
                    {"path": "./backend/app/main.py", "language": "python"},
                    {"path": ".github/workflows/ci.yml", "language": "yaml"},
                ]
            )
        ),
    )["repository_context"]

    assert [f["path"] for f in repository["files"]] == [
        ".github/workflows/ci.yml",
        "backend/app/main.py",
    ]
    assert repository["top_level_paths"] == [".github", "backend"]


@pytest.mark.parametrize(
    "write_field",
    ["local_path", "checkout_path", "clone_url_writable", "command", "write"],
)
def test_ac2_repository_analysis_rejects_write_operations(client, write_field):
    """AC2: "must not modify the target repository", enforced two ways.

    1. The request contract *rejects* any field that would ask for a write --
       ``extra="forbid"`` means an unknown key is a 422, not a silently ignored
       one, so no caller can smuggle a checkout path or shell command in.
    2. Serving the request performs no write, delete, or subprocess call.

    The existing mutation guard only wraps a direct ``build_repository_context``
    call; this exercises the same guard across the real HTTP route, which is the
    surface a downstream consumer actually calls.
    """
    payload = governed_request(repository=repository_input(**{write_field: "/srv/checkout"}))

    with no_repository_mutation():
        rejected = assemble(client, payload)
        accepted = assemble(client, governed_request())

    assert rejected.status_code == 422, (
        f"repository.{write_field} was accepted instead of rejected: {rejected.text}"
    )
    assert write_field in rejected.text

    # The clean request still succeeds under the guard: read-only is the normal
    # path, not an error path.
    assert accepted.status_code == 200, accepted.text
    repository = accepted.json()["repository_context"]
    assert repository["read_only"] is True
    assert repository["analysis_mode"] == service.REPOSITORY_ANALYSIS_MODE


@pytest.mark.parametrize("commit_sha", ["short", "zzzzzzz", "   "])
def test_ac2_invalid_commit_sha_is_rejected(client, commit_sha):
    response = assemble(client, governed_request(repository=repository_input(commit_sha=commit_sha)))

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# AC3 -- Knowledge Context reuse (no parallel retrieval mechanism)
# ---------------------------------------------------------------------------


def test_ac3_context_packages_and_governed_context_share_one_mechanism():
    """Both features must call the same selection and hashing helpers."""
    assert packages_routes.select_approved_entries is knowledge_context.select_approved_entries
    assert packages_routes.compute_entry_context_hash is knowledge_context.compute_entry_context_hash

    # The governed-context service must not carry its own KB query/hash.
    assert service.compute_entry_context_hash is knowledge_context.compute_entry_context_hash
    assert not hasattr(service, "select")


def test_ac3_knowledge_hash_matches_the_shared_capability(client, kb_entries):
    knowledge = assemble_ok(client, governed_request())["knowledge_context"]

    expected = knowledge_context.compute_entry_context_hash([make_entry(APPROVED_ENTRY_ID)])
    assert knowledge["knowledge_hash"] == expected
    assert knowledge["source_capability"] == "knowledge_context_assembly"


def test_ac3_knowledge_selection_order_does_not_change_the_hash(client):
    forward = assemble_ok(
        client, governed_request(entry_ids=[APPROVED_ENTRY_ID, SECOND_APPROVED_ENTRY_ID])
    )
    reverse = assemble_ok(
        client, governed_request(entry_ids=[SECOND_APPROVED_ENTRY_ID, APPROVED_ENTRY_ID])
    )

    assert forward["knowledge_context"]["knowledge_hash"] == reverse["knowledge_context"]["knowledge_hash"]
    assert forward["context_hash"] == reverse["context_hash"]


def _called_names(module) -> set[str]:
    """Every callable name invoked in a module's source (``a.f(...)`` -> ``f``)."""
    names: set[str] = set()
    for node in ast.walk(ast.parse(inspect.getsource(module))):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            names.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            names.add(node.func.attr)
    return names


def test_knowledge_context_reuse_not_duplication():
    """AC3: the governed-context modules carry no knowledge retrieval of their own.

    ``packages_routes`` sharing the helper (asserted above) says nothing about
    the governed-context caller. This binds the caller itself to the shared
    capability and proves, from the source, that neither the governed-context
    route nor its service builds a parallel KB query.
    """
    assert (
        context_assembly_routes.select_approved_entries
        is knowledge_context.select_approved_entries
    )

    # Guard: the shared capability really is where the KB query lives, so the
    # absence checks below are meaningful rather than vacuous.
    shared = _called_names(knowledge_context)
    assert {"select", "execute", "scalars"} <= shared

    for module in (context_assembly_routes, service):
        duplicated = _called_names(module) & {"select", "execute", "scalars"}
        assert not duplicated, f"{module.__name__} builds its own KB retrieval: {duplicated}"


@pytest.mark.parametrize(
    "endpoint, expected_status",
    [
        ("/api/governed-context/assemble", 200),
        ("/api/governed-context/lock", 201),
    ],
)
def test_ac3_every_governed_entry_point_delegates_to_the_shared_selection(
    client, session, monkeypatch, endpoint, expected_status
):
    """The knowledge section is produced by the shared capability, once."""
    calls: list[tuple[object, list[str]]] = []
    real_select = knowledge_context.select_approved_entries

    async def spy(db, entry_ids):
        calls.append((db, list(entry_ids)))
        return await real_select(db, entry_ids)

    monkeypatch.setattr(context_assembly_routes, "select_approved_entries", spy)

    response = client.post(endpoint, json=governed_request())
    assert response.status_code == expected_status, response.text

    assert calls == [(session, [APPROVED_ENTRY_ID])]
    # Exactly one KB round-trip: no parallel retrieval ran alongside the shared one.
    assert len(session.statements) == 1


def test_ac3_lock_status_also_routes_knowledge_through_the_shared_selection(
    client, session, monkeypatch
):
    """The third governed entry point delegates too.

    ``/lock/status`` re-assembles the current context to compare it against a
    lock, so it retrieves knowledge just like the other two endpoints. Covering
    only ``/assemble`` and ``/lock`` would leave a governed entry point free to
    grow its own retrieval.
    """
    payload = governed_request()
    lock = client.post("/api/governed-context/lock", json=payload)
    assert lock.status_code == 201, lock.text

    calls: list[list[str]] = []
    real_select = knowledge_context.select_approved_entries

    async def spy(db, entry_ids):
        calls.append(list(entry_ids))
        return await real_select(db, entry_ids)

    monkeypatch.setattr(context_assembly_routes, "select_approved_entries", spy)
    statements_before = len(session.statements)

    response = lock_status(client, lock.json(), payload)
    assert response.status_code == 200, response.text
    assert response.json()["stale"] is False

    assert calls == [[APPROVED_ENTRY_ID]]
    assert len(session.statements) - statements_before == 1


def test_ac3_knowledge_context_is_populated_from_the_shared_service_return_value(
    client, monkeypatch
):
    """AC3: the response section is built from what the shared service returned.

    Every other AC3 assertion still holds if ``knowledge_context`` echoed the
    requested ``entry_ids`` back, because the fixtures request exactly the
    entries the KB holds -- echo and real population are indistinguishable
    there. Here the shared capability returns an entry the caller never asked
    for, so only a section genuinely built from its return value can pass.
    """
    substitute = make_entry(
        SECOND_APPROVED_ENTRY_ID,
        title="Supplied only by the shared selection",
        content="Returned by knowledge_context.select_approved_entries.",
        source="confluence://eng/shared-selection",
    )

    async def only_source_of_knowledge(db, entry_ids):
        return [substitute]

    monkeypatch.setattr(
        context_assembly_routes, "select_approved_entries", only_source_of_knowledge
    )

    knowledge = assemble_ok(client, governed_request(entry_ids=[APPROVED_ENTRY_ID]))[
        "knowledge_context"
    ]

    assert knowledge["entry_ids"] == [SECOND_APPROVED_ENTRY_ID]
    assert knowledge["entry_count"] == 1
    assert [p["title"] for p in knowledge["provenance"]] == [substitute.title]
    assert [p["source"] for p in knowledge["provenance"]] == [substitute.source]
    assert knowledge["knowledge_hash"] == knowledge_context.compute_entry_context_hash(
        [substitute]
    )
    # The requested id is nowhere in the section: nothing echoed the request and
    # no second retrieval merged its own rows in alongside the shared one.
    assert APPROVED_ENTRY_ID not in knowledge["entry_ids"]
    assert APPROVED_ENTRY_ID not in [p["entry_id"] for p in knowledge["provenance"]]


def _imported_names(module) -> dict[str, str]:
    """Map every name a module imports to the module it was imported from."""
    origins: dict[str, str] = {}
    for node in ast.walk(ast.parse(inspect.getsource(module))):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                origins[alias.asname or alias.name] = node.module or ""
        elif isinstance(node, ast.Import):
            for alias in node.names:
                origins[alias.asname or alias.name] = alias.name
    return origins


def test_ac3_governed_context_modules_import_no_retrieval_machinery_of_their_own():
    """AC3, at the import layer: there is nothing to build a parallel query with.

    ``test_knowledge_context_reuse_not_duplication`` scans call names against
    ``{select, execute, scalars}``. That set misses the query-builder verbs the
    shared capability actually uses (``where``, ``in_``) and every other
    retrieval form (``text``, ``query``, ``fetchall``, ``scalar_one``). This
    checks the imports instead: a module that imports no query API cannot grow
    a duplicate retrieval path, however it is spelled.
    """
    service_sqlalchemy = {
        name: origin
        for name, origin in _imported_names(service).items()
        if origin.split(".")[0] == "sqlalchemy"
    }
    assert not service_sqlalchemy, (
        f"the governed-context service imports query machinery: {service_sqlalchemy}"
    )

    route_sqlalchemy = {
        name: origin
        for name, origin in _imported_names(context_assembly_routes).items()
        if origin.split(".")[0] == "sqlalchemy"
    }
    # AsyncSession is the dependency annotation handed straight to the shared
    # capability -- a type, not a way to query.
    assert set(route_sqlalchemy) <= {"AsyncSession"}, (
        f"the governed-context route imports query machinery: {route_sqlalchemy}"
    )

    route_imports = _imported_names(context_assembly_routes)
    for name in ("select_approved_entries", "UnapprovedEntryError", "UnknownEntryIdsError"):
        assert route_imports.get(name) == "app.services.knowledge_context", (
            f"{name} does not come from the shared Knowledge Context capability"
        )

    query_builder_calls = {
        "text",
        "query",
        "where",
        "in_",
        "fetchall",
        "fetchone",
        "scalar",
        "scalar_one",
        "scalar_one_or_none",
        "exec_driver_sql",
        "stream",
    }
    # Guard: these verbs really do mark KB retrieval -- the shared capability
    # uses them -- so their absence below is evidence rather than vacuous.
    assert _called_names(knowledge_context) & query_builder_calls
    for module in (context_assembly_routes, service):
        duplicated = _called_names(module) & query_builder_calls
        assert not duplicated, f"{module.__name__} builds its own KB query: {duplicated}"


def test_ac3_governed_context_service_has_no_database_reach():
    """AC3: ``context_assembly.py`` receives knowledge, it never fetches it.

    Retrieval needs an awaitable round-trip over a session. The service exposes
    neither: every public function is synchronous and none accepts a database
    handle, so knowledge can only reach it as entries the shared capability
    already selected. That makes a duplicate retrieval path structurally
    impossible rather than merely absent today.
    """
    public = {
        name: obj
        for name, obj in vars(service).items()
        if inspect.isfunction(obj)
        and obj.__module__ == service.__name__
        and not name.startswith("_")
    }
    assert public, "no public governed-context service functions were inspected"

    for name, func in public.items():
        assert not inspect.iscoroutinefunction(func), (
            f"{name} is async -- a KB round-trip could hide behind it"
        )
        parameters = inspect.signature(func).parameters
        handles = [p for p in parameters if p in {"db", "session", "conn", "connection"}]
        assert not handles, f"{name} accepts a database handle: {handles}"
        sessionish = [
            p for p, spec in parameters.items() if "Session" in str(spec.annotation)
        ]
        assert not sessionish, f"{name} is annotated with a session type: {sessionish}"

    # Knowledge enters the service only as entries the shared capability chose.
    entries_param = inspect.signature(service.build_knowledge_context).parameters["entries"]
    assert "Sequence[Entry]" in str(entries_param.annotation)


# ---------------------------------------------------------------------------
# AC4 -- Approved knowledge enforcement
# ---------------------------------------------------------------------------


def test_ac4_resolved_entries_are_treated_as_approved_knowledge(client):
    knowledge = assemble_ok(client, governed_request())["knowledge_context"]

    assert knowledge["approved_status"] == "resolved"
    assert knowledge["entry_ids"] == [APPROVED_ENTRY_ID]
    assert knowledge["entry_count"] == 1


@pytest.mark.parametrize(
    "status",
    [
        EntryStatus.OPEN,
        EntryStatus.DEFERRED,
        EntryStatus.SUPERSEDED,
        EntryStatus.DRAFT,
        EntryStatus.PENDING_REVIEW,
        EntryStatus.ARCHIVED,
        EntryStatus.REJECTED,
    ],
)
def test_ac4_ineligible_knowledge_is_rejected_never_silently_included(session, client, status):
    session.entries = [make_entry(UNAPPROVED_ENTRY_ID, status=status)]

    response = assemble(client, governed_request(entry_ids=[UNAPPROVED_ENTRY_ID]))

    # Rejected loudly: no assembly is produced at all, so nothing can slip in.
    assert response.status_code == 400
    assert UNAPPROVED_ENTRY_ID in response.text
    assert "knowledge_context" not in response.json()


def test_ac4_mixed_selection_fails_rather_than_dropping_the_unapproved_entry(client):
    response = assemble(
        client, governed_request(entry_ids=[APPROVED_ENTRY_ID, UNAPPROVED_ENTRY_ID])
    )

    assert response.status_code == 400
    assert UNAPPROVED_ENTRY_ID in response.text


def test_ac4_unknown_entry_id_is_a_404(client):
    response = assemble(client, governed_request(entry_ids=[MISSING_ENTRY_ID]))

    assert response.status_code == 404
    assert MISSING_ENTRY_ID in response.text


def test_ac4_malformed_entry_id_is_a_404_not_a_crash(client):
    response = assemble(client, governed_request(entry_ids=["not-a-uuid"]))

    assert response.status_code == 404


def test_ac4_empty_knowledge_selection_is_allowed(client):
    knowledge = assemble_ok(client, governed_request(entry_ids=[]))["knowledge_context"]

    assert knowledge["entry_ids"] == []
    assert knowledge["entry_count"] == 0
    assert knowledge["knowledge_hash"].startswith("sha256:")


# Ids for the lifecycle states the seeded KB does not otherwise cover. Kept in
# this module so the shared fixture KB stays exactly as the other tests expect.
DRAFT_ENTRY_ID = "44444444-4444-4444-8444-444444444444"
ARCHIVED_ENTRY_ID = "55555555-5555-4555-8555-555555555555"


def _mixed_lifecycle_kb() -> list[Entry]:
    """A KB holding draft, resolved and archived knowledge side by side."""
    return [
        make_entry(
            DRAFT_ENTRY_ID,
            title="Draft caching proposal",
            content="Unreviewed caching notes.",
            source="confluence://eng/caching",
            status=EntryStatus.DRAFT,
        ),
        make_entry(APPROVED_ENTRY_ID),
        make_entry(
            SECOND_APPROVED_ENTRY_ID,
            title="Approved logging standard",
            content="Structured JSON logs only.",
            source="confluence://eng/logging",
        ),
        make_entry(
            ARCHIVED_ENTRY_ID,
            title="Retired deploy runbook",
            content="Superseded deploy steps.",
            source="confluence://eng/deploy-old",
            status=EntryStatus.ARCHIVED,
        ),
    ]


def test_approved_knowledge_enforcement(session, client):
    """AC4: with draft/resolved/archived knowledge present, only resolved is assembled.

    The rejection tests above prove an *explicitly selected* ineligible entry is
    refused. They say nothing about the success path: when the KB also holds
    ineligible lifecycle states, the assembled section must contain the resolved
    entries and nothing else. That is the "must not silently enter" half of AC4,
    and it is the half that was never asserted.
    """
    session.entries = _mixed_lifecycle_kb()
    resolved_ids = [APPROVED_ENTRY_ID, SECOND_APPROVED_ENTRY_ID]

    response = assemble(client, governed_request(entry_ids=resolved_ids))
    assert response.status_code == 200, response.text
    knowledge = response.json()["knowledge_context"]

    assert knowledge["approved_status"] == EntryStatus.RESOLVED.value == "resolved"
    assert knowledge["entry_ids"] == resolved_ids
    assert knowledge["entry_count"] == len(resolved_ids)

    # Every assembled item states its identity and the status that made it eligible.
    assert [item["entry_id"] for item in knowledge["provenance"]] == resolved_ids
    for item in knowledge["provenance"]:
        assert item["status"] == EntryStatus.RESOLVED.value, item

    # Nothing ineligible leaked into any part of the assembly, not just this section.
    for ineligible in (DRAFT_ENTRY_ID, ARCHIVED_ENTRY_ID):
        assert ineligible not in response.text


def test_ac4_ineligible_knowledge_does_not_reach_the_hash_or_digest(session, client):
    """AC4: ineligible entries are absent from the governed hash, not just the listing.

    Excluding an entry from ``provenance`` while still folding it into the
    knowledge hash would let unapproved knowledge influence the governed context
    invisibly. Assembling the same selection against a resolved-only KB and
    against the mixed-lifecycle KB must produce byte-identical output.
    """
    payload = governed_request(entry_ids=[APPROVED_ENTRY_ID, SECOND_APPROVED_ENTRY_ID])
    mixed = _mixed_lifecycle_kb()

    session.entries = [e for e in mixed if e.status is EntryStatus.RESOLVED]
    resolved_only = assemble_ok(client, payload)

    session.entries = mixed
    with_ineligible = assemble_ok(client, payload)

    assert with_ineligible["knowledge_context"] == resolved_only["knowledge_context"]
    assert with_ineligible["context_hash"] == resolved_only["context_hash"]


# Every lifecycle state that is *not* approved knowledge, derived from the model
# instead of hand-listed, so a state added to ``EntryStatus`` later cannot enter
# a governed context with no test standing in its way.
NON_APPROVED_STATUSES = [s for s in EntryStatus if s is not EntryStatus.RESOLVED]

THIRD_APPROVED_ENTRY_ID = "66666666-6666-4666-8666-666666666666"


def test_ac4_resolved_is_the_only_lifecycle_state_that_counts_as_approved():
    """AC4: the approved-knowledge gate is pinned to ``status='resolved'``.

    Every other AC4 test leans on this one constant. Widening it to a tuple, or
    repointing it at another lifecycle state, would leave the per-status
    rejection tests passing for the states they happen to name while the gate
    itself admitted something new.
    """
    assert knowledge_context.APPROVED_ENTRY_STATUS is EntryStatus.RESOLVED
    assert EntryStatus.RESOLVED.value == "resolved"
    assert NON_APPROVED_STATUSES, "EntryStatus must define states other than resolved"


@pytest.mark.parametrize("entry_status", NON_APPROVED_STATUSES, ids=lambda s: s.value)
def test_ac4_no_lifecycle_state_other_than_resolved_is_ever_approved(
    session, client, entry_status
):
    """AC4, enumerated from ``EntryStatus`` rather than from a hand-written list.

    ``test_ac4_ineligible_knowledge_is_rejected_never_silently_included`` spells
    its statuses out literally, and that list is already one short: ``published``
    is a lifecycle state, is not approved knowledge, and nothing covered it.
    Deriving the parametrisation from the enum closes that gap and keeps it
    closed as the lifecycle model grows.
    """
    session.entries = [make_entry(UNAPPROVED_ENTRY_ID, status=entry_status)]

    response = assemble(client, governed_request(entry_ids=[UNAPPROVED_ENTRY_ID]))

    assert response.status_code == 400, response.text
    # Refused outright: no assembly exists, so nothing was silently populated.
    assert "knowledge_context" not in response.json()
    assert UNAPPROVED_ENTRY_ID in response.text


def test_ac4_only_the_selected_resolved_entries_enter_the_context(session, client):
    """AC4: eligibility filters the *selection*, it is not "everything resolved".

    Here the KB holds three approved entries and the caller asks for one. A gate
    that returned every resolved row -- or that dropped the id filter and leaned
    on approval alone -- would still satisfy every "nothing unapproved leaked"
    assertion above while over-sharing approved knowledge into the assembly.
    """
    session.entries = _mixed_lifecycle_kb() + [
        make_entry(
            THIRD_APPROVED_ENTRY_ID,
            title="Approved incident playbook",
            content="Page the on-call rota first.",
            source="confluence://eng/incidents",
        )
    ]

    response = assemble(client, governed_request(entry_ids=[SECOND_APPROVED_ENTRY_ID]))
    assert response.status_code == 200, response.text
    knowledge = response.json()["knowledge_context"]

    assert knowledge["entry_ids"] == [SECOND_APPROVED_ENTRY_ID]
    assert knowledge["entry_count"] == 1
    assert [p["entry_id"] for p in knowledge["provenance"]] == [SECOND_APPROVED_ENTRY_ID]
    # Approved but unselected knowledge stays out of the governed context entirely.
    for unselected in (APPROVED_ENTRY_ID, THIRD_APPROVED_ENTRY_ID):
        assert unselected not in response.text


def test_ac4_a_rejection_names_every_ineligible_entry_not_just_the_first(session, client):
    """AC4: a mixed selection is refused wholesale, and reports all of it.

    Reporting only the first offender invites a caller to retry id-by-id and
    reassemble a context the gate never approved as a set.
    """
    session.entries = [
        make_entry(APPROVED_ENTRY_ID),
        make_entry(UNAPPROVED_ENTRY_ID, status=EntryStatus.OPEN),
        make_entry(DRAFT_ENTRY_ID, status=EntryStatus.DRAFT),
    ]

    response = assemble(
        client,
        governed_request(
            entry_ids=[APPROVED_ENTRY_ID, UNAPPROVED_ENTRY_ID, DRAFT_ENTRY_ID]
        ),
    )

    assert response.status_code == 400, response.text
    detail = response.json()["detail"]
    assert UNAPPROVED_ENTRY_ID in detail
    assert DRAFT_ENTRY_ID in detail
    # No partial assembly: the one approved entry did not come back on its own.
    assert "knowledge_context" not in response.json()


@pytest.mark.parametrize(
    "endpoint",
    ["/api/governed-context/assemble", "/api/governed-context/lock"],
)
def test_ac4_no_governed_entry_point_admits_unapproved_knowledge(client, endpoint):
    """AC4 holds on every way into the assembly, not just ``/assemble``.

    ``/lock`` assembles before it locks. If enforcement lived in the assemble
    handler alone, locking would be a way to mint a downstream artefact over
    knowledge the gate refuses.
    """
    response = client.post(endpoint, json=governed_request(entry_ids=[UNAPPROVED_ENTRY_ID]))

    assert response.status_code == 400, response.text
    body = response.json()
    assert "knowledge_context" not in body
    assert "governed_inputs" not in body  # no lock was minted either


def test_ac4_lock_status_refuses_to_compare_against_unapproved_knowledge(client):
    """The staleness endpoint re-assembles the current context, so it is a third way in."""
    lock = client.post("/api/governed-context/lock", json=governed_request())
    assert lock.status_code == 201, lock.text

    response = lock_status(
        client, lock.json(), governed_request(entry_ids=[UNAPPROVED_ENTRY_ID])
    )

    assert response.status_code == 400, response.text
    # Not answered as "fresh" or "stale" -- the comparison never happened.
    assert "stale" not in response.json()


def test_ac4_the_shared_selection_itself_enforces_approval(kb_entries):
    """AC4 at the service boundary, underneath the HTTP mapping.

    ``select_approved_entries`` is the single gate the governed routes and
    Context Packages share. Proving the filter here means a future caller that
    bypasses the router cannot bypass the enforcement with it.
    """
    stub = StubSession(kb_entries)

    approved = asyncio.run(
        knowledge_context.select_approved_entries(stub, [APPROVED_ENTRY_ID])
    )
    assert [str(e.id) for e in approved] == [APPROVED_ENTRY_ID]
    assert all(e.status is EntryStatus.RESOLVED for e in approved)

    with pytest.raises(knowledge_context.UnapprovedEntryError) as excinfo:
        asyncio.run(
            knowledge_context.select_approved_entries(
                stub, [APPROVED_ENTRY_ID, UNAPPROVED_ENTRY_ID]
            )
        )

    # The caller is told exactly which ids were refused and receives no entries.
    assert excinfo.value.entry_ids == [UNAPPROVED_ENTRY_ID]


# ---------------------------------------------------------------------------
# AC5 -- Engineering Governance Context and conflict detection
# ---------------------------------------------------------------------------


def test_ac5_approved_governance_is_represented_in_the_assembly(client):
    governance = assemble_ok(client, governed_request())["governance_context"]

    assert [rule["id"] for rule in governance["rules"]] == ["GOV-1"]
    assert governance["rules"][0]["topic"] == "database-migrations"
    assert governance["rules"][0]["source"] == "engineering-handbook"
    assert governance["excluded_rule_ids"] == []


def test_ac5_unapproved_governance_is_excluded_not_silently_accepted(client):
    body = assemble_ok(
        client,
        governed_request(
            governance=[
                governance_input(),
                governance_input(id="GOV-DRAFT", topic="code-review", status="draft"),
            ]
        ),
    )
    governance = body["governance_context"]

    assert governance["excluded_rule_ids"] == ["GOV-DRAFT"]
    assert "GOV-DRAFT" not in [rule["id"] for rule in governance["rules"]]


def test_ac5_conflicting_governance_is_detected_rather_than_accepted(client):
    response = assemble(
        client,
        governed_request(
            governance=[
                governance_input(id="GOV-A", rule="Migrations must be reversible."),
                governance_input(id="GOV-B", rule="Migrations may be irreversible."),
            ]
        ),
    )

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["error"] == "governance_conflict"
    assert detail["conflicts"][0]["topic"] == "database-migrations"
    assert detail["conflicts"][0]["rule_ids"] == ["GOV-A", "GOV-B"]


def test_ac5_higher_precedence_resolves_a_disagreement_and_records_it(client):
    governance = assemble_ok(
        client,
        governed_request(
            governance=[
                governance_input(id="GOV-A", rule="Migrations must be reversible.", precedence=1),
                governance_input(id="GOV-B", rule="Migrations may be irreversible.", precedence=0),
            ]
        ),
    )["governance_context"]

    assert [rule["id"] for rule in governance["rules"]] == ["GOV-A"]
    assert governance["superseded"] == [
        {
            "topic": "database-migrations",
            "superseded_rule_id": "GOV-B",
            "superseded_by_rule_id": "GOV-A",
        }
    ]


def test_ac5_same_rule_from_two_sources_is_not_a_conflict(client):
    governance = assemble_ok(
        client,
        governed_request(
            governance=[
                governance_input(id="GOV-A", rule="Migrations must be reversible."),
                governance_input(id="GOV-B", rule="  migrations   MUST be reversible. "),
            ]
        ),
    )["governance_context"]

    assert len(governance["rules"]) == 1


def test_ac5_unrelated_topics_do_not_conflict(client):
    governance = assemble_ok(
        client,
        governed_request(
            governance=[
                governance_input(id="GOV-A", topic="database-migrations"),
                governance_input(id="GOV-B", topic="code-review", rule="Two approvals required."),
            ]
        ),
    )["governance_context"]

    assert [rule["id"] for rule in governance["rules"]] == ["GOV-B", "GOV-A"]


def test_governance_context_inclusion(client):
    """AC5: approved standards, policies and guidance reach the final assembly.

    Governance inputs are posted under the request's ``governance`` key (see
    ``GovernedContextRequest``); every approved rule must appear in the
    ``governance_context`` section with its lineage intact, and must
    participate in the assembly's digests.
    """
    rules = [
        governance_input(
            id="STD-1",
            title="Reversible migrations",
            topic="database-migrations",
            rule="Every migration must define a downgrade path.",
            source="engineering-standards",
        ),
        governance_input(
            id="POL-1",
            title="Two-approval policy",
            topic="code-review",
            rule="Every change requires two approvals.",
            source="engineering-policies",
        ),
        governance_input(
            id="GUI-1",
            title="Structured logging guidance",
            topic="logging",
            rule="Prefer structured logs over free-text messages.",
            source="engineering-guidance",
        ),
    ]

    body = assemble_ok(client, governed_request(governance=rules))

    assert "governance_context" in body
    governance = body["governance_context"]
    assert sorted(rule["id"] for rule in governance["rules"]) == ["GUI-1", "POL-1", "STD-1"]
    assert governance["excluded_rule_ids"] == []
    assert governance["superseded"] == []

    by_id = {rule["id"]: rule for rule in governance["rules"]}
    for supplied in rules:
        included = by_id[supplied["id"]]
        assert included["title"] == supplied["title"]
        assert included["topic"] == supplied["topic"]
        assert included["rule"] == supplied["rule"]
        assert included["source"] == supplied["source"]
        assert included["precedence"] == supplied["precedence"]

    # Included, not merely echoed: the section is digested into the assembly.
    assert body["input_digests"]["governance_context"] == governance["digest"]
    assert body["context_hash"] != assemble_ok(client, governed_request())["context_hash"]


def test_governance_conflict_detection(client):
    """AC5: conflicting governance is detected *before* the assembly completes.

    The shipped contract answers an unresolvable governance conflict with
    ``409 Conflict`` and a structured description, not the ``422`` used for
    malformed payloads -- see ``context_assembly.py`` and the frontend status
    map in ``useGovernedContextService.ts``. This test pins that contract;
    ``test_ac5_malformed_governance_input_is_a_422`` covers the 422 boundary.
    """
    conflicting = [
        governance_input(
            id="STD-1",
            topic="database-migrations",
            rule="Migrations must always be reversible.",
        ),
        governance_input(
            id="STD-2",
            topic="database-migrations",
            rule="Migrations may be irreversible when data loss is intended.",
        ),
    ]

    response = assemble(client, governed_request(governance=conflicting))

    assert response.status_code == 409, response.text
    body = response.json()
    # No assembly was produced: the conflict short-circuits the request.
    assert "context_hash" not in body
    assert "governance_context" not in body

    detail = body["detail"]
    assert detail["error"] == "governance_conflict"
    assert "database-migrations" in detail["message"]

    assert len(detail["conflicts"]) == 1
    conflict = detail["conflicts"][0]
    assert conflict["topic"] == "database-migrations"
    assert conflict["rule_ids"] == ["STD-1", "STD-2"]
    assert conflict["reason"], "the conflict must describe why it is unresolvable"


@pytest.mark.parametrize(
    "broken",
    [
        {"id": ""},
        {"rule": ""},
        {"topic": ""},
        {"precedence": "high"},
        {"unexpected_field": "x"},
    ],
    ids=["empty-id", "empty-rule", "empty-topic", "non-integer-precedence", "extra-field"],
)
def test_ac5_malformed_governance_input_is_a_422(client, broken):
    """Malformed governance input is a 422 contract error, distinct from 409.

    Keeping the two apart matters: 422 means "this payload is not governance",
    while 409 means "this governance cannot be reconciled".
    """
    response = assemble(client, governed_request(governance=[governance_input(**broken)]))

    assert response.status_code == 422, response.text


def test_ac5_lock_status_refuses_to_compare_against_conflicting_governance(client):
    """AC5 on the third way in: ``/lock/status`` re-assembles ``current``.

    ``test_ac12_conflicting_governance_blocks_the_whole_assembly`` pins
    ``/assemble`` and ``/lock``. The staleness endpoint assembles too, so
    without this it would stay a route where conflicting governance is
    answered with a freshness verdict instead of being detected.
    """
    lock = client.post("/api/governed-context/lock", json=governed_request())
    assert lock.status_code == 201, lock.text

    response = lock_status(
        client,
        lock.json(),
        governed_request(
            governance=[
                governance_input(id="GOV-A", rule="Migrations must be reversible."),
                governance_input(id="GOV-B", rule="Migrations may be irreversible."),
            ]
        ),
    )

    assert response.status_code == 409, response.text
    body = response.json()
    # Not silently answered as fresh or stale -- the comparison never happened.
    assert "stale" not in body
    assert "current_context_hash" not in body
    assert body["detail"]["error"] == "governance_conflict"


def test_ac5_conflict_detection_lives_in_the_service_not_the_route(client):
    """AC5 at the service boundary, underneath the HTTP mapping.

    ``build_governance_context`` is the single gate. Proving it raises here
    means a future caller that assembles without going through the router
    cannot obtain a governance context over irreconcilable rules -- the error
    is raised in place of the section, so there is nothing to pass on.
    """
    conflicting = [
        service.GovernanceRuleInput(
            **governance_input(id="GOV-A", rule="Migrations must be reversible.")
        ),
        service.GovernanceRuleInput(
            **governance_input(id="GOV-B", rule="Migrations may be irreversible.")
        ),
    ]

    with pytest.raises(service.GovernanceConflictError) as excinfo:
        service.build_governance_context(conflicting)

    conflicts = excinfo.value.conflicts
    assert [c.topic for c in conflicts] == ["database-migrations"]
    assert conflicts[0].rule_ids == ["GOV-A", "GOV-B"]
    assert "database-migrations" in str(excinfo.value)

    # The same inputs over HTTP surface that service-level conflict as 409.
    response = assemble(client, governed_request(governance=[r.model_dump() for r in conflicting]))
    assert response.status_code == 409, response.text
    assert response.json()["detail"]["conflicts"][0]["rule_ids"] == ["GOV-A", "GOV-B"]


def test_ac5_every_conflicting_topic_is_reported_not_just_the_first(client):
    """A second conflicting topic must not be swallowed by the first.

    Reporting one conflict at a time would let a caller "fix" governance
    topic-by-topic while later contradictions stayed invisible until the next
    round trip.
    """
    response = assemble(
        client,
        governed_request(
            governance=[
                governance_input(id="LOG-A", topic="logging", rule="Logs must be structured."),
                governance_input(id="LOG-B", topic="logging", rule="Logs must be free text."),
                governance_input(id="REV-A", topic="code-review", rule="Two approvals required."),
                governance_input(id="REV-B", topic="code-review", rule="One approval is enough."),
                # A third, uncontested topic is still not enough to let the
                # request through with a partial governance section.
                governance_input(id="MIG-A", topic="database-migrations"),
            ]
        ),
    )

    assert response.status_code == 409, response.text
    body = response.json()
    assert "governance_context" not in body
    conflicts = body["detail"]["conflicts"]
    assert [c["topic"] for c in conflicts] == ["code-review", "logging"]
    assert [c["rule_ids"] for c in conflicts] == [["REV-A", "REV-B"], ["LOG-A", "LOG-B"]]
    assert all(c["reason"] for c in conflicts)


def test_ac5_conflict_detection_does_not_depend_on_input_order(client):
    """The same contradiction submitted either way round is the same conflict.

    Order-sensitive detection would make silent acceptance a matter of how the
    caller happened to sort its rules.
    """
    first = governance_input(id="GOV-A", rule="Migrations must be reversible.")
    second = governance_input(id="GOV-B", rule="Migrations may be irreversible.")

    forward = assemble(client, governed_request(governance=[first, second]))
    reversed_ = assemble(client, governed_request(governance=[second, first]))

    assert forward.status_code == reversed_.status_code == 409
    assert forward.json()["detail"] == reversed_.json()["detail"]


def test_ac5_an_unapproved_rule_is_excluded_rather_than_read_as_a_conflict(client):
    """Exclusion and conflict are different answers, and neither hides the other.

    A draft rule contradicting an approved one is not a governance conflict --
    it was never applicable. It must still be reported as excluded, so its
    contradiction is visible rather than dropped without trace.
    """
    body = assemble_ok(
        client,
        governed_request(
            governance=[
                governance_input(id="GOV-APPROVED", rule="Migrations must be reversible."),
                governance_input(
                    id="GOV-DRAFT", rule="Migrations may be irreversible.", status="draft"
                ),
            ]
        ),
    )
    governance = body["governance_context"]

    assert [rule["id"] for rule in governance["rules"]] == ["GOV-APPROVED"]
    assert governance["excluded_rule_ids"] == ["GOV-DRAFT"]
    assert governance["rules"][0]["rule"] == "Migrations must be reversible."

    # And the exclusion path cannot be used to mute a genuine conflict: adding
    # a second *approved* contradiction is still detected.
    response = assemble(
        client,
        governed_request(
            governance=[
                governance_input(id="GOV-APPROVED", rule="Migrations must be reversible."),
                governance_input(
                    id="GOV-DRAFT", rule="Migrations may be irreversible.", status="draft"
                ),
                governance_input(id="GOV-OTHER", rule="Migrations may be irreversible."),
            ]
        ),
    )
    assert response.status_code == 409, response.text
    assert response.json()["detail"]["conflicts"][0]["rule_ids"] == ["GOV-APPROVED", "GOV-OTHER"]


def test_ac5_only_the_tied_top_precedence_rules_are_named_in_the_conflict(client):
    """Precedence resolves what it can; the unresolvable tie is what is reported.

    A rule that is cleanly superseded is not part of the contradiction, so
    naming it would send the caller to change governance that already lost.
    """
    response = assemble(
        client,
        governed_request(
            governance=[
                governance_input(id="GOV-TOP-A", rule="Migrations must be reversible.", precedence=2),
                governance_input(id="GOV-TOP-B", rule="Migrations may be irreversible.", precedence=2),
                governance_input(id="GOV-LOW", rule="Migrations are discouraged.", precedence=0),
            ]
        ),
    )

    assert response.status_code == 409, response.text
    conflicts = response.json()["detail"]["conflicts"]
    assert len(conflicts) == 1
    assert conflicts[0]["rule_ids"] == ["GOV-TOP-A", "GOV-TOP-B"]
    assert "GOV-LOW" not in conflicts[0]["rule_ids"]


def test_ac5_no_governance_input_is_an_explicit_empty_section(client):
    """Governance is optional, and "none supplied" is stated rather than missing.

    The section is still emitted and still digested, so an assembly built with
    no governance is distinguishable from one built with it -- which is what
    keeps AC11's ``governance_context`` staleness reason meaningful.
    """
    body = assemble_ok(client, governed_request(governance=[]))
    governance = body["governance_context"]

    assert governance["rules"] == []
    assert governance["excluded_rule_ids"] == []
    assert governance["superseded"] == []
    assert governance["digest"]
    assert body["input_digests"]["governance_context"] == governance["digest"]
    assert governance["digest"] != assemble_ok(client, governed_request())[
        "governance_context"
    ]["digest"]


# ---------------------------------------------------------------------------
# AC6 -- Integrated Context Assembly
# ---------------------------------------------------------------------------


def test_ac6_four_sections_combine_into_one_structure(client):
    body = assemble_ok(client, governed_request())

    for section in (
        "requirement_context",
        "repository_context",
        "knowledge_context",
        "governance_context",
    ):
        assert body[section], f"missing section: {section}"

    assert body["assembly_version"] == service.GOVERNED_ASSEMBLY_VERSION
    assert set(body["input_digests"]) == {
        "requirement_context",
        "repository_context",
        "knowledge_context",
        "governance_context",
    }
    assert body["context_hash"].startswith("sha256:")
    assert body["created_at"]


def test_ac6_input_digests_match_each_section_digest(client):
    body = assemble_ok(client, governed_request())

    for section, digest in body["input_digests"].items():
        assert body[section]["digest"] == digest


def test_integrated_context_assembly_all_sections(session, client):
    """AC6: one call over all four input types returns one Governed Context Assembly.

    ``test_ac6_four_sections_combine_into_one_structure`` proves the four keys
    exist for the default fixture. This proves the integration itself: a
    *single* POST carrying requirement, repository, knowledge and governance
    inputs comes back as one assembly object in which each section is derived
    from its own supplied input -- no section defaulted, echoed empty, or
    fetched by a second round trip.
    """
    request = request_input(
        id="MDSU-345-AC6",
        title="Integrated Context Assembly",
        description="Combine all four governed inputs into one structure.",
        acceptance_criteria=["All four sections present in one assembly"],
        source="jira",
    )
    repository = repository_input(
        branch="feature/MDSU-345-Governed-Context-Assembly",
        commit_sha="0f1e2d3c4b5a697",
        files=[
            {
                "path": "backend/app/routes/context_assembly.py",
                "language": "python",
                "role": "route",
            },
            {
                "path": "frontend/src/services/useGovernedContextService.ts",
                "language": "typescript",
                "role": "service",
            },
        ],
    )
    governance = [
        governance_input(
            id="STD-7",
            title="Structured logging standard",
            topic="observability",
            rule="Every service emits structured JSON logs.",
            source="engineering-standards",
        )
    ]
    entry_ids = [APPROVED_ENTRY_ID, SECOND_APPROVED_ENTRY_ID]

    # Exactly one API call -- the integration point AC6 is about.
    response = assemble(
        client,
        governed_request(
            request=request,
            repository=repository,
            entry_ids=entry_ids,
            governance=governance,
        ),
    )
    assert response.status_code == 200, response.text
    body = response.json()

    # One assembly object, not a list or a per-section envelope.
    assert isinstance(body, dict)
    assert set(body) == {
        "assembly_version",
        "requirement_context",
        "repository_context",
        "knowledge_context",
        "governance_context",
        "input_digests",
        "context_hash",
        "created_at",
    }

    # Each section carries the input that was posted alongside the other three.
    requirement = body["requirement_context"]
    assert requirement["request_id"] == "MDSU-345-AC6"
    assert requirement["title"] == request["title"]
    assert requirement["description"] == request["description"]
    assert requirement["acceptance_criteria"] == request["acceptance_criteria"]
    assert requirement["source"] == "jira"

    repository_context = body["repository_context"]
    assert repository_context["commit_sha"] == "0f1e2d3c4b5a697"
    assert repository_context["branch"] == repository["branch"]
    assert repository_context["file_count"] == 2
    assert repository_context["languages"] == ["python", "typescript"]
    assert repository_context["top_level_paths"] == ["backend", "frontend"]
    assert repository_context["read_only"] is True

    knowledge = body["knowledge_context"]
    assert knowledge["entry_ids"] == sorted(entry_ids)
    assert knowledge["entry_count"] == 2
    assert knowledge["approved_status"] == EntryStatus.RESOLVED.value
    assert [p["entry_id"] for p in knowledge["provenance"]] == sorted(entry_ids)

    governance_context = body["governance_context"]
    assert [rule["id"] for rule in governance_context["rules"]] == ["STD-7"]
    assert governance_context["rules"][0]["rule"] == governance[0]["rule"]

    # The four sections are combined, not merely co-located: every section is
    # digested into the one assembly and the assembly hash is derived from all
    # four together.
    digests = body["input_digests"]
    assert set(digests) == {
        "requirement_context",
        "repository_context",
        "knowledge_context",
        "governance_context",
    }
    assert all(digests[section] == body[section]["digest"] for section in digests)
    assert len(set(digests.values())) == 4, "each section must digest independently"
    assert body["context_hash"] == service.compute_assembly_hash(digests)
    assert body["assembly_version"] == service.GOVERNED_ASSEMBLY_VERSION

    # Knowledge was resolved inside that same call, via one selection query.
    assert len(session.statements) == 1


# The four governed sections, paired with the model each one must serialise
# from. Driving the assertions below off the models rather than a hand-written
# field list means a section field added to the contract but never populated by
# the assembly is a failure here, not a silently absent key on the wire.
_AC6_SECTION_MODELS = {
    "requirement_context": RequirementAnalysisContext,
    "repository_context": RepositoryAnalysisContext,
    "knowledge_context": KnowledgeContext,
    "governance_context": EngineeringGovernanceContext,
}
_AC6_SECTIONS = tuple(_AC6_SECTION_MODELS)


def test_ac6_all_four_sections_are_required_by_the_assembly_contract():
    """AC6: the combined structure cannot lose a section and still validate.

    ``test_ac6_four_sections_combine_into_one_structure`` observes four keys in
    one happy-path response. That stays green if a section is later made
    optional and starts defaulting to ``None`` whenever its builder is skipped.
    This pins the contract itself: each section is a required field of the
    declared type, so an assembly missing one cannot be constructed at all.
    """
    fields = GovernedContextAssembly.model_fields

    for section, model in _AC6_SECTION_MODELS.items():
        field = fields[section]
        assert field.is_required(), f"{section} must not be optional or defaulted"
        assert field.annotation is model, (
            f"{section} must serialise {model.__name__}, got {field.annotation}"
        )

    with pytest.raises(ValidationError) as excinfo:
        GovernedContextAssembly(
            assembly_version=service.GOVERNED_ASSEMBLY_VERSION,
            input_digests={},
            context_hash="sha256:0",
            created_at="2026-08-16T00:00:00+00:00",
        )
    missing = {error["loc"][0] for error in excinfo.value.errors()}
    assert missing == set(_AC6_SECTIONS)


@pytest.mark.parametrize("section", _AC6_SECTIONS)
def test_ac6_every_declared_section_field_reaches_the_response(client, section):
    """AC6: "structured", checked field by field rather than key by key.

    The section objects are asserted piecemeal elsewhere; this checks the whole
    declared surface of each one survives serialisation, so a consumer reading
    the contract finds every field it was promised.
    """
    body = assemble_ok(client, governed_request())

    missing = [name for name in _AC6_SECTION_MODELS[section].model_fields if name not in body[section]]
    assert not missing, f"{section} dropped declared fields on the wire: {missing}"


def test_ac6_supplying_inputs_populates_the_sections_rather_than_defaulting_them(client):
    """AC6: "all four are populated when inputs provided".

    Presence alone is weak evidence -- ``knowledge_context`` and
    ``governance_context`` are structurally present even with nothing selected.
    Assembling the empty baseline and the fully populated request through the
    same endpoint shows the populated response is built from the inputs, not
    echoed from a default shape that happens to carry the right keys.
    """
    baseline = assemble_ok(client, governed_request(entry_ids=[], governance=[]))
    populated = assemble_ok(
        client,
        governed_request(
            entry_ids=[APPROVED_ENTRY_ID, SECOND_APPROVED_ENTRY_ID],
            governance=[
                governance_input(),
                governance_input(
                    id="GOV-2",
                    title="Structured logging",
                    topic="observability",
                    rule="Services emit structured JSON logs.",
                ),
            ],
        ),
    )

    # Both responses are the same four-section structure: an empty section is
    # still a section, so "populated" is a content difference, not a shape one.
    for section in _AC6_SECTIONS:
        assert section in baseline, f"empty input dropped {section} from the assembly"
        assert section in populated

    assert baseline["knowledge_context"]["entry_ids"] == []
    assert baseline["knowledge_context"]["entry_count"] == 0
    assert baseline["knowledge_context"]["provenance"] == []
    assert baseline["governance_context"]["rules"] == []

    assert populated["knowledge_context"]["entry_ids"] == sorted(
        [APPROVED_ENTRY_ID, SECOND_APPROVED_ENTRY_ID]
    )
    assert populated["knowledge_context"]["entry_count"] == 2
    assert len(populated["knowledge_context"]["provenance"]) == 2
    assert [rule["id"] for rule in populated["governance_context"]["rules"]] == [
        "GOV-1",
        "GOV-2",
    ]

    # Requirement and repository were populated in both, from their own inputs.
    for body in (baseline, populated):
        assert body["requirement_context"]["title"] == request_input()["title"]
        assert body["repository_context"]["commit_sha"] == repository_input()["commit_sha"]
        assert body["repository_context"]["file_count"] == 2


_AC6_CHANGED_INPUT = {
    "requirement_context": lambda: governed_request(
        request=request_input(title="A different engineering request")
    ),
    "repository_context": lambda: governed_request(
        repository=repository_input(commit_sha="9999999")
    ),
    "knowledge_context": lambda: governed_request(entry_ids=[SECOND_APPROVED_ENTRY_ID]),
    "governance_context": lambda: governed_request(
        governance=[
            governance_input(id="GOV-9", rule="Every migration ships a rollback script.")
        ]
    ),
}


@pytest.mark.parametrize("changed", _AC6_SECTIONS)
def test_ac6_each_section_is_derived_only_from_its_own_input(client, changed):
    """AC6: the four contexts are *combined*, not blended into one another.

    AC10 proves a changed governed input changes the aggregate
    ``context_hash``. That would still hold if repository information leaked
    into ``requirement_context``, or if one section were rebuilt from the whole
    payload. Changing exactly one input must move exactly one section and leave
    the other three byte-identical -- which is what makes the combined
    structure readable section by section downstream.
    """
    baseline = assemble_ok(client, governed_request())
    variant = assemble_ok(client, _AC6_CHANGED_INPUT[changed]())

    assert variant[changed] != baseline[changed], f"{changed} ignored its own input"

    for section in _AC6_SECTIONS:
        if section == changed:
            continue
        assert variant[section] == baseline[section], (
            f"changing the {changed} input also changed {section}"
        )

    # The one moved section still propagates into the combined identity.
    assert variant["input_digests"][changed] != baseline["input_digests"][changed]
    assert variant["context_hash"] != baseline["context_hash"]


@pytest.mark.parametrize(
    "payload,expected_status",
    [
        pytest.param(
            lambda: governed_request(repository=repository_input(commit_sha="nope")),
            422,
            id="invalid-repository-input",
        ),
        pytest.param(
            lambda: governed_request(entry_ids=[UNAPPROVED_ENTRY_ID]),
            400,
            id="unapproved-knowledge",
        ),
        pytest.param(
            lambda: governed_request(
                governance=[
                    governance_input(id="GOV-A", rule="Migrations must be reversible."),
                    governance_input(id="GOV-B", rule="Migrations may be irreversible."),
                ]
            ),
            409,
            id="conflicting-governance",
        ),
    ],
)
def test_ac6_a_rejected_input_yields_no_partial_assembly(client, payload, expected_status):
    """AC6: one assembly operation, so there is no half-assembled result.

    Whichever section refuses its input, the caller gets an error body -- never
    a structure carrying the three sections that did build, which a consumer
    could mistake for a complete Governed Context Assembly.
    """
    response = assemble(client, payload())

    assert response.status_code == expected_status, response.text
    body = response.json()
    leaked = [section for section in _AC6_SECTIONS if section in body]
    assert not leaked, f"partial assembly leaked sections: {leaked}"
    assert "context_hash" not in body
    assert "input_digests" not in body


# ---------------------------------------------------------------------------
# AC7 -- Context Assembly Lock
# ---------------------------------------------------------------------------


def test_ac7_successful_assembly_converts_into_a_lock(client):
    payload = governed_request()
    assembly = assemble_ok(client, payload)

    response = client.post("/api/governed-context/lock", json=payload)
    assert response.status_code == 201, response.text
    lock = response.json()

    assert lock["lock_id"].startswith("lock-")
    assert lock["context_hash"] == assembly["context_hash"]
    assert lock["assembly_version"] == assembly["assembly_version"]
    assert lock["input_digests"] == assembly["input_digests"]


def test_ac7_lock_identifies_the_governed_inputs_it_came_from(client):
    payload = governed_request()
    assembly = assemble_ok(client, payload)
    lock = client.post("/api/governed-context/lock", json=payload).json()

    governed = lock["governed_inputs"]
    assert governed["request_id"] == "MDSU-345"
    assert governed["request_digest"] == assembly["requirement_context"]["digest"]
    assert governed["repository_commit_sha"] == "abc1234def5678"
    assert governed["repository_digest"] == assembly["repository_context"]["digest"]
    assert governed["knowledge_entry_ids"] == [APPROVED_ENTRY_ID]
    assert governed["knowledge_hash"] == assembly["knowledge_context"]["knowledge_hash"]
    assert governed["governance_rule_ids"] == ["GOV-1"]
    assert governed["governance_digest"] == assembly["governance_context"]["digest"]


def test_ac7_a_failed_assembly_produces_no_lock(client):
    response = client.post(
        "/api/governed-context/lock",
        json=governed_request(entry_ids=[UNAPPROVED_ENTRY_ID]),
    )

    assert response.status_code == 400
    assert "lock_id" not in response.json()


def test_context_assembly_lock_creation(client):
    """AC7: assembling then locking yields a lock naming its governed inputs.

    The two tests above cover the default single-entry/single-rule fixture and
    say nothing about ``created_at``. This proves the lock over a *distinct*
    input set -- two KB entries, two governance rules, a non-default commit --
    so every governed-input field has to be derived from what was posted rather
    than echoed from a fixture, and pins the timestamp the contract promises.

    Field naming follows the shipped contract (``GovernedInputsRef``):
    ``request_digest`` is the requirement digest and ``governance_rule_ids``
    the governance IDs. The key set is asserted explicitly so a rename shows up
    here instead of silently passing.
    """
    repository = repository_input(
        branch="feature/MDSU-345-Governed-Context-Assembly",
        commit_sha="9f8e7d6c5b4a321",
    )
    governance = [
        governance_input(),
        governance_input(
            id="GOV-2",
            title="Structured logging standard",
            topic="observability",
            rule="Every service emits structured JSON logs.",
        ),
    ]
    entry_ids = [SECOND_APPROVED_ENTRY_ID, APPROVED_ENTRY_ID]
    payload = governed_request(
        repository=repository, entry_ids=entry_ids, governance=governance
    )

    assembly = assemble_ok(client, payload)

    response = client.post("/api/governed-context/lock", json=payload)
    assert response.status_code == 201, response.text
    lock = response.json()

    # The lock is a ContextAssemblyLock, not a bare hash or an echoed assembly.
    assert set(lock) == {
        "lock_id",
        "assembly_version",
        "context_hash",
        "input_digests",
        "governed_inputs",
        "created_at",
    }
    assert ContextAssemblyLock.model_validate(lock).context_hash == lock["context_hash"]

    # It carries the hash of the assembly it was produced from.
    assert lock["context_hash"] == assembly["context_hash"]
    assert lock["assembly_version"] == assembly["assembly_version"]
    assert lock["input_digests"] == assembly["input_digests"]
    assert lock["lock_id"] == f"lock-{assembly['context_hash'].removeprefix('sha256:')[:16]}"

    # It identifies the governed inputs it was produced from -- all four.
    governed = lock["governed_inputs"]
    assert set(governed) == {
        "request_id",
        "request_digest",
        "repository_commit_sha",
        "repository_digest",
        "knowledge_entry_ids",
        "knowledge_hash",
        "governance_rule_ids",
        "governance_digest",
    }

    assert governed["request_id"] == "MDSU-345"
    assert governed["request_digest"] == assembly["requirement_context"]["digest"]

    assert governed["repository_commit_sha"] == "9f8e7d6c5b4a321"
    assert governed["repository_digest"] == assembly["repository_context"]["digest"]

    assert governed["knowledge_entry_ids"] == sorted(entry_ids)
    assert governed["knowledge_entry_ids"] == assembly["knowledge_context"]["entry_ids"]
    assert governed["knowledge_hash"] == assembly["knowledge_context"]["knowledge_hash"]

    assert governed["governance_rule_ids"] == ["GOV-1", "GOV-2"]
    assert governed["governance_digest"] == assembly["governance_context"]["digest"]

    # A real creation timestamp: parseable, timezone-aware UTC ISO-8601.
    created_at = datetime.fromisoformat(lock["created_at"])
    assert created_at.tzinfo is not None
    assert created_at.utcoffset() == timedelta(0)

    # ...and the timestamp is metadata only: it must not enter the hash, or
    # AC9's deterministic-hash guarantee would not survive a second lock.
    assert lock["context_hash"] == service.compute_assembly_hash(lock["input_digests"])


GOVERNED_INPUT_FIELDS = {
    "request_id",
    "request_digest",
    "repository_commit_sha",
    "repository_digest",
    "knowledge_entry_ids",
    "knowledge_hash",
    "governance_rule_ids",
    "governance_digest",
}


def lock_ok(client, payload: dict) -> dict:
    response = client.post("/api/governed-context/lock", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.parametrize(
    ("payload", "expected_changes"),
    [
        pytest.param(
            governed_request(request=request_input(title="Add governed context locking")),
            {"request_digest"},
            id="requirement-source",
        ),
        pytest.param(
            governed_request(repository=repository_input(commit_sha="0badc0ffee1234")),
            {"repository_commit_sha", "repository_digest"},
            id="repository-commit",
        ),
        pytest.param(
            governed_request(entry_ids=[SECOND_APPROVED_ENTRY_ID]),
            {"knowledge_entry_ids", "knowledge_hash"},
            id="knowledge-entries",
        ),
        pytest.param(
            governed_request(governance=[governance_input(id="GOV-9", rule="Never skip a review.")]),
            {"governance_rule_ids", "governance_digest"},
            id="governance-sources",
        ),
    ],
)
def test_ac7_each_governed_input_field_tracks_only_its_own_source(
    client, payload: dict, expected_changes: set[str]
):
    """AC7: the lock must *identify* its governed inputs, not merely carry a hash.

    ``test_context_assembly_lock_creation`` proves the field values for one
    input set. That would still pass if the lock stamped a constant, or if it
    smeared every input across every field. This changes exactly one governed
    input at a time and asserts precisely which ``governed_inputs`` fields move
    -- so each provenance field is pinned to the source it claims to identify.
    """
    baseline = lock_ok(client, governed_request())["governed_inputs"]
    changed = lock_ok(client, payload)["governed_inputs"]

    assert set(changed) == GOVERNED_INPUT_FIELDS
    moved = {field for field in GOVERNED_INPUT_FIELDS if changed[field] != baseline[field]}
    assert moved == expected_changes


def test_ac7_lock_from_the_frontend_payload_shape_names_every_governed_input(client):
    """AC7 across the FE/BE seam: the browser posts a *thinner* payload.

    ``buildGovernedContextRequest`` (frontend/src/composables/useContextAssemblyLock.ts)
    sends no ``request.id``, no acceptance criteria, and no repository ``url``
    or ``files`` -- it has none to send. The lock must still name all four
    governed inputs, and ``request_id`` must be an explicit ``null`` rather
    than a missing key, because the frontend's ``GovernedInputsRef`` types it
    as ``string | null`` and renders straight off it.
    """
    payload = {
        "request": {
            "title": "Add infusion guard",
            "description": "Guard the pump rate against out-of-range doses.",
            "source": "metamorphic-kb:workspace/ws-1/package/pkg-persistent-1",
        },
        "repository": {"name": "metamorphic-kb", "branch": "main", "commit_sha": "abc1234"},
        "knowledge": {"entry_ids": [APPROVED_ENTRY_ID]},
        "governance": [
            {
                "id": "gov-1",
                "title": "logging",
                "topic": "logging",
                "rule": "Log every dose change.",
                "status": "approved",
                "precedence": 0,
            }
        ],
    }

    assembly = assemble_ok(client, payload)
    governed = lock_ok(client, payload)["governed_inputs"]

    assert set(governed) == GOVERNED_INPUT_FIELDS
    assert governed["request_id"] is None
    assert governed["request_digest"] == assembly["requirement_context"]["digest"]
    assert governed["repository_commit_sha"] == "abc1234"
    assert governed["repository_digest"] == assembly["repository_context"]["digest"]
    assert governed["knowledge_entry_ids"] == [APPROVED_ENTRY_ID]
    assert governed["knowledge_hash"] == assembly["knowledge_context"]["knowledge_hash"]
    assert governed["governance_rule_ids"] == ["gov-1"]
    assert governed["governance_digest"] == assembly["governance_context"]["digest"]


def test_ac7_a_lock_over_no_approved_knowledge_still_records_the_empty_selection(client):
    """An empty KB selection is a governed input too, not an absent one.

    AC4 allows locking with no approved knowledge. The lineage fields must then
    say "nothing was selected" -- an empty list and a real hash over it -- so a
    downstream consumer can tell an empty selection apart from stripped
    provenance.
    """
    payload = governed_request(entry_ids=[])
    assembly = assemble_ok(client, payload)
    governed = lock_ok(client, payload)["governed_inputs"]

    assert set(governed) == GOVERNED_INPUT_FIELDS
    assert governed["knowledge_entry_ids"] == []
    assert governed["knowledge_hash"] == assembly["knowledge_context"]["knowledge_hash"]
    assert governed["knowledge_hash"]
    # The other three inputs are untouched by an empty knowledge selection.
    assert governed["repository_commit_sha"] == "abc1234def5678"
    assert governed["governance_rule_ids"] == ["GOV-1"]


def test_ac7_the_lock_is_consumable_downstream_exactly_as_it_was_issued(client):
    """"Suitable for downstream consumption" means: no reshaping required.

    A consumer that stores the lock response verbatim and hands it back must be
    understood. This round-trips the wire body through ``ContextAssemblyLock``
    (no field lost, none invented) and feeds the untouched body to the
    staleness endpoint, which is the only downstream consumer in the contract.
    """
    payload = governed_request()
    lock = lock_ok(client, payload)

    revalidated = ContextAssemblyLock.model_validate(lock)
    assert revalidated.model_dump(mode="json") == lock

    status = client.post(
        "/api/governed-context/lock/status", json={"lock": lock, "current": payload}
    )
    assert status.status_code == 200, status.text
    assert status.json()["lock_id"] == lock["lock_id"]


def test_ac7_the_frontend_lock_contract_declares_the_same_fields_as_the_backend():
    """The browser types the lock by hand; drift there is a silent contract break.

    ``frontend/src/types/governedContext.ts`` mirrors the Pydantic models, and
    the frontend lock tests assert against hand-written fixtures shaped by
    those types. If a field is renamed on either side the fixtures keep passing
    on their own, so the two declarations are compared here instead.
    """
    contract = (
        Path(__file__).resolve().parents[2] / "frontend/src/types/governedContext.ts"
    )
    if not contract.exists():  # backend-only checkout
        pytest.skip("frontend contract file is not present in this checkout")
    source = contract.read_text(encoding="utf-8")

    def declared_fields(type_name: str) -> set[str]:
        block = re.search(rf"export type {type_name} = \{{\n(.*?)\n\}}", source, re.DOTALL)
        assert block, f"{type_name} is no longer declared in {contract.name}"
        return set(re.findall(r"^  (\w+)\??:", block.group(1), re.MULTILINE))

    assert declared_fields("GovernedInputsRef") == set(GovernedInputsRef.model_fields)
    assert declared_fields("GovernedInputsRef") == GOVERNED_INPUT_FIELDS
    assert declared_fields("ContextAssemblyLock") == set(ContextAssemblyLock.model_fields)


# ---------------------------------------------------------------------------
# AC8 -- Provenance and source lineage
# ---------------------------------------------------------------------------


def test_ac8_kb_derived_knowledge_retains_provenance(client):
    knowledge = assemble_ok(client, governed_request())["knowledge_context"]

    assert len(knowledge["provenance"]) == 1
    provenance = knowledge["provenance"][0]
    assert provenance["entry_id"] == APPROVED_ENTRY_ID
    assert provenance["title"] == "Retry policy for ingestion"
    assert provenance["source"] == "confluence://eng/retry-policy"
    assert provenance["version"] == "2026-08-01T12:30:00+00:00"
    assert provenance["updated_at"] == "2026-08-01T12:30:00+00:00"
    assert provenance["status"] == "resolved"


def test_ac8_provenance_is_emitted_for_every_selected_entry(client):
    knowledge = assemble_ok(
        client, governed_request(entry_ids=[APPROVED_ENTRY_ID, SECOND_APPROVED_ENTRY_ID])
    )["knowledge_context"]

    assert [p["entry_id"] for p in knowledge["provenance"]] == [
        APPROVED_ENTRY_ID,
        SECOND_APPROVED_ENTRY_ID,
    ]
    assert knowledge["entry_ids"] == [APPROVED_ENTRY_ID, SECOND_APPROVED_ENTRY_ID]


def test_ac8_missing_optional_lineage_is_null_not_fabricated(session, client):
    session.entries = [make_entry(APPROVED_ENTRY_ID, source=None)]

    knowledge = assemble_ok(client, governed_request())["knowledge_context"]

    assert knowledge["provenance"][0]["source"] is None
    assert knowledge["provenance"][0]["entry_id"] == APPROVED_ENTRY_ID


def test_provenance_and_source_lineage(session, client):
    """AC8: every assembled item keeps its own lineage, and each section stays traceable.

    The tests above pin the lineage of a *single* seeded entry against hardcoded
    literals, so an implementation that broadcast one entry's title, source and
    timestamp across every provenance item would still pass them. This seeds two
    approved entries whose lineage differs in every field and checks each
    assembled item against the KB row it was derived from -- then checks the two
    non-KB sections carry the identifiers that make the rest of the governed
    context traceable to its origin (``request_id``/``source`` for the
    requirement, ``commit_sha`` for the repository).
    """
    rows = {
        APPROVED_ENTRY_ID: make_entry(
            APPROVED_ENTRY_ID,
            title="Retry policy for ingestion",
            source="confluence://eng/retry-policy",
            updated_at=datetime(2026, 8, 1, 12, 30, tzinfo=timezone.utc),
        ),
        SECOND_APPROVED_ENTRY_ID: make_entry(
            SECOND_APPROVED_ENTRY_ID,
            title="Approved logging standard",
            content="Structured JSON logs only.",
            source="confluence://eng/logging",
            updated_at=datetime(2026, 8, 9, 6, 45, tzinfo=timezone.utc),
        ),
    }
    session.entries = list(rows.values())

    request = request_input(id="MDSU-345-AC8", source="jira://MDSU-345")
    repository = repository_input(commit_sha="9d8c7b6a5e4f3d2")
    body = assemble_ok(
        client,
        governed_request(request=request, repository=repository, entry_ids=list(rows)),
    )

    provenance = body["knowledge_context"]["provenance"]
    assert len(provenance) == len(rows)
    assert {p["entry_id"] for p in provenance} == set(rows)

    for item in provenance:
        # The lineage AC8 requires is present, and populated rather than null.
        assert {"entry_id", "source", "title", "updated_at"} <= set(item), item
        assert all(item[field] for field in ("entry_id", "source", "title", "updated_at"))

        # ...and it is the lineage of the row this item actually came from.
        entry = rows[item["entry_id"]]
        assert item["title"] == entry.title
        assert item["source"] == entry.source
        assert item["updated_at"] == entry.updated_at.isoformat()
        # AC8 asks for "version or updated timestamp"; the contract emits both.
        assert item["version"] == entry.updated_at.isoformat()
        assert item["status"] == entry.status.value

    # Lineage is per-entry: no field collapsed onto a shared value.
    for field in ("entry_id", "title", "source", "updated_at"):
        assert len({item[field] for item in provenance}) == len(rows), field

    # The sections that are not KB-derived stay traceable to their own sources.
    requirement = body["requirement_context"]
    assert requirement["request_id"] == "MDSU-345-AC8"
    assert requirement["source"] == "jira://MDSU-345"

    assert body["repository_context"]["commit_sha"] == "9d8c7b6a5e4f3d2"


AC8_LINEAGE_FIELDS = {"entry_id", "source", "title", "version", "updated_at"}


def test_ac8_no_digest_covers_title_or_source_so_lineage_needs_its_own_guard(session, client):
    """Why AC8 cannot be inferred from the hash tests: the hash does not see it.

    ``compute_entry_context_hash`` reduces entries to ``{id, content}`` and the
    knowledge digest hashes only ``{entry_id, version}``. ``title`` and
    ``source`` therefore sit outside every digest and outside ``context_hash``,
    so an assembly that stripped or rewrote them would leave AC9/AC10/AC11
    entirely green. This pins that blind spot, which is what makes the
    field-level assertions in this section load-bearing rather than redundant.
    """
    common = {"content": "Ingestion retries use exponential backoff."}
    session.entries = [
        make_entry(
            APPROVED_ENTRY_ID,
            title="Retry policy for ingestion",
            source="confluence://eng/retry-policy",
            **common,
        )
    ]
    first = assemble_ok(client, governed_request())

    session.entries = [
        make_entry(
            APPROVED_ENTRY_ID,
            title="Renamed retry policy",
            source="notion://eng/retry-policy",
            **common,
        )
    ]
    second = assemble_ok(client, governed_request())

    # Identical hashed material: lineage changes are invisible to every digest.
    assert first["knowledge_context"]["knowledge_hash"] == second["knowledge_context"][
        "knowledge_hash"
    ]
    assert first["knowledge_context"]["digest"] == second["knowledge_context"]["digest"]
    assert first["context_hash"] == second["context_hash"]

    # ...yet the lineage itself must still travel with the assembled context.
    assert first["knowledge_context"]["provenance"][0]["title"] == "Retry policy for ingestion"
    assert second["knowledge_context"]["provenance"][0]["title"] == "Renamed retry policy"
    assert (
        first["knowledge_context"]["provenance"][0]["source"]
        != second["knowledge_context"]["provenance"][0]["source"]
    )


def test_ac8_each_provenance_item_tracks_its_own_entry_under_reversed_selection(
    session, client
):
    """Lineage must be paired per entry, not zipped against the requested order.

    Assembly emits entries sorted by id while the caller selects them in
    whatever order it likes. If provenance were built from the sorted rows but
    labelled from the request order, lineage would be silently attributed to
    the wrong entry -- a corruption no hash test can see. The selection here is
    deliberately the reverse of the emitted order so that mispairing shows up.
    """
    rows = {
        APPROVED_ENTRY_ID: make_entry(
            APPROVED_ENTRY_ID,
            title="Retry policy for ingestion",
            source="confluence://eng/retry-policy",
            updated_at=datetime(2026, 8, 1, 12, 30, tzinfo=timezone.utc),
        ),
        SECOND_APPROVED_ENTRY_ID: make_entry(
            SECOND_APPROVED_ENTRY_ID,
            title="Approved logging standard",
            content="Structured JSON logs only.",
            source="confluence://eng/logging",
            updated_at=datetime(2026, 8, 9, 6, 45, tzinfo=timezone.utc),
        ),
    }
    session.entries = list(rows.values())

    knowledge = assemble_ok(
        client,
        governed_request(entry_ids=[SECOND_APPROVED_ENTRY_ID, APPROVED_ENTRY_ID]),
    )["knowledge_context"]

    provenance = knowledge["provenance"]
    # Emission order is the deterministic sorted order, not the request order.
    assert [p["entry_id"] for p in provenance] == sorted(rows)
    # ...and the id list the rest of the contract exposes agrees with it.
    assert knowledge["entry_ids"] == [p["entry_id"] for p in provenance]
    assert knowledge["entry_count"] == len(rows)

    for item in provenance:
        entry = rows[item["entry_id"]]
        assert item["title"] == entry.title
        assert item["source"] == entry.source
        assert item["updated_at"] == entry.updated_at.isoformat()
        assert item["version"] == entry.updated_at.isoformat()


def test_ac8_lineage_strings_are_carried_verbatim_not_normalised(session, client):
    """Provenance must be the KB's own values, not a cleaned-up rendering.

    Assembly normalises plenty of other input (requests are stripped, paths are
    de-prefixed, governance topics are casefolded). Applying any of that to
    lineage would break the link back to the KB row, so the awkward values here
    must survive byte-for-byte.
    """
    title = "  Retry   policy: ingestion & back-off  "
    source = "confluence://eng/retry-policy?version=3&mode=strict#Ábschnitt"
    session.entries = [make_entry(APPROVED_ENTRY_ID, title=title, source=source)]

    provenance = assemble_ok(client, governed_request())["knowledge_context"]["provenance"][0]

    assert provenance["title"] == title
    assert provenance["source"] == source
    assert provenance["entry_id"] == APPROVED_ENTRY_ID


def test_ac8_the_lineage_contract_keeps_every_field_and_stays_required():
    """The declared contract, not just one response, has to carry AC8's fields.

    Turning ``entry_id``/``title`` into optionals would let a future assembly
    emit ``null`` lineage while every response-shape assertion above still
    passed, so the declaration itself is pinned here.
    """
    fields = KnowledgeProvenance.model_fields
    assert AC8_LINEAGE_FIELDS <= set(fields)

    # Identity and approval state are always knowable, so they are never null.
    for name in ("entry_id", "title", "status"):
        assert fields[name].is_required(), name
    # AC8 asks for these "where available": optional, but always declared.
    for name in ("source", "version", "updated_at"):
        assert not fields[name].is_required(), name

    assert KnowledgeContext.model_fields["provenance"].annotation == list[KnowledgeProvenance]


def test_ac8_provenance_survives_the_declared_response_contract(client):
    """A downstream consumer parsing the shipped contract still sees lineage.

    ``response_model`` drops anything the model does not declare, so the wire
    payload is re-parsed through the published models here: this proves the
    lineage reaches consumers rather than only existing inside the service.
    """
    body = assemble_ok(client, governed_request())

    parsed = GovernedContextAssembly.model_validate(body)

    assert len(parsed.knowledge_context.provenance) == 1
    item = parsed.knowledge_context.provenance[0]
    assert item.entry_id == APPROVED_ENTRY_ID
    assert item.title == "Retry policy for ingestion"
    assert item.source == "confluence://eng/retry-policy"
    assert item.updated_at == "2026-08-01T12:30:00+00:00"
    assert item.version == item.updated_at
    assert AC8_LINEAGE_FIELDS <= set(item.model_dump())


def test_ac8_the_frontend_provenance_contract_declares_the_same_lineage_fields():
    """The browser hand-types provenance; drift there loses lineage silently.

    Same guard AC7 applies to the lock: the frontend fixtures are shaped by
    ``governedContext.ts``, so a field renamed or dropped on either side keeps
    both suites green unless the two declarations are compared directly.
    """
    contract = (
        Path(__file__).resolve().parents[2] / "frontend/src/types/governedContext.ts"
    )
    if not contract.exists():  # backend-only checkout
        pytest.skip("frontend contract file is not present in this checkout")
    source = contract.read_text(encoding="utf-8")

    block = re.search(
        r"export type KnowledgeProvenance = \{\n(.*?)\n\}", source, re.DOTALL
    )
    assert block, f"KnowledgeProvenance is no longer declared in {contract.name}"
    declared = set(re.findall(r"^  (\w+)\??:", block.group(1), re.MULTILINE))

    assert AC8_LINEAGE_FIELDS <= declared
    assert declared == set(KnowledgeProvenance.model_fields)


# ---------------------------------------------------------------------------
# AC9 -- Deterministic context hash
# ---------------------------------------------------------------------------


def test_ac9_identical_inputs_produce_the_same_context_hash(client):
    payload = governed_request()

    first = assemble_ok(client, payload)
    second = assemble_ok(client, payload)

    assert first["context_hash"] == second["context_hash"]
    assert first["input_digests"] == second["input_digests"]
    # created_at is wall-clock and must never feed the hash.
    assert "created_at" not in first["input_digests"]


def test_ac9_repeated_locks_of_unchanged_inputs_share_an_identity(client):
    payload = governed_request()

    first = client.post("/api/governed-context/lock", json=payload).json()
    second = client.post("/api/governed-context/lock", json=payload).json()

    assert first["lock_id"] == second["lock_id"]
    assert first["context_hash"] == second["context_hash"]


def test_ac9_governance_input_ordering_does_not_change_the_hash(client):
    rules = [
        governance_input(id="GOV-A", topic="database-migrations"),
        governance_input(id="GOV-B", topic="code-review", rule="Two approvals required."),
    ]

    forward = assemble_ok(client, governed_request(governance=rules))
    reverse = assemble_ok(client, governed_request(governance=list(reversed(rules))))

    assert forward["context_hash"] == reverse["context_hash"]


def test_deterministic_context_hash(session, client, monkeypatch):
    """AC9: repeating an assembly with unchanged inputs re-derives the same hash.

    The test above posts *the same dict object* twice and asserts the hashes
    match, so it cannot distinguish a genuinely canonical hash from one that
    happens to reuse cached or shared state — and a constant would satisfy it.
    This pins determinism properly:

    * each call gets a freshly built payload, sharing no mutable object;
    * the wall clock is advanced between calls, so a timestamp leaking into the
      hashed material would break the run rather than pass unnoticed;
    * the KB rows are re-seeded as new ORM instances, so the hash is shown to
      follow entry content rather than object identity or row ordering;
    * the hash is recomputed from the published section digests, and a changed
      requirement is asserted to move it — without that, "identical" would be
      trivially true for a constant.
    """

    def seed_knowledge() -> None:
        # Fresh instances with identical data on every call.
        session.entries = [
            make_entry(SECOND_APPROVED_ENTRY_ID, content="Structured JSON logs only."),
            make_entry(APPROVED_ENTRY_ID),
        ]

    def fixed_payload() -> dict:
        return governed_request(
            request=request_input(id="MDSU-345-AC9"),
            repository=repository_input(commit_sha="abc1234def5678"),
            entry_ids=[APPROVED_ENTRY_ID, SECOND_APPROVED_ENTRY_ID],
            governance=[
                governance_input(id="GOV-1"),
                governance_input(
                    id="GOV-2", topic="code-review", rule="Two approvals required."
                ),
            ],
        )

    ticks: list[int] = []

    def moving_clock() -> str:
        ticks.append(len(ticks))
        base = datetime(2026, 8, 16, 9, 0, tzinfo=timezone.utc)
        return (base + timedelta(minutes=len(ticks))).isoformat()

    monkeypatch.setattr(service, "_now", moving_clock)

    runs = []
    for _ in range(3):
        seed_knowledge()
        runs.append(assemble_ok(client, fixed_payload()))

    first = runs[0]
    context_hash = first["context_hash"]

    assert {run["context_hash"] for run in runs} == {context_hash}
    for run in runs[1:]:
        assert run["input_digests"] == first["input_digests"]
        assert run["assembly_version"] == first["assembly_version"]

    # The clock moved between the calls and the hash did not follow it.
    assert len({run["created_at"] for run in runs}) == len(runs)

    # The hash is the canonical function of the published section digests, so
    # any consumer can recompute it from the assembly it was handed.
    assert context_hash == service.compute_assembly_hash(first["input_digests"])
    assert context_hash.startswith("sha256:")
    assert len(context_hash.removeprefix("sha256:")) == 64

    # Determinism carries into the lock derived from the same governed inputs.
    seed_knowledge()
    lock = client.post("/api/governed-context/lock", json=fixed_payload())
    assert lock.status_code == 201, lock.text
    assert lock.json()["context_hash"] == context_hash

    # Guard: the assertions above would all hold for a constant hash.
    changed = fixed_payload()
    changed["request"] = request_input(id="MDSU-345-AC9", description="A different requirement.")
    seed_knowledge()
    assert assemble_ok(client, changed)["context_hash"] != context_hash


def _run_hash_probe(**env_overrides: str) -> dict:
    """Run ``tests/_ac9_hash_probe.py`` in a fresh interpreter and read its hash."""
    backend_root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "PYTHONPATH": str(backend_root), **env_overrides}
    completed = subprocess.run(
        [sys.executable, str(Path(__file__).with_name("_ac9_hash_probe.py"))],
        capture_output=True,
        text=True,
        cwd=str(backend_root),
        env=env,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


@pytest.mark.parametrize(
    ("label", "env"),
    [
        # A different string-hash seed changes set/dict-of-set iteration order
        # and the value of ``hash()`` for every str in the process.
        ("hash-seed", {"PYTHONHASHSEED": "12345"}),
        # A C locale with UTF-8 mode off changes the platform default encoding.
        ("locale", {"PYTHONHASHSEED": "0", "LC_ALL": "C", "LANG": "C", "PYTHONUTF8": "0"}),
    ],
)
def test_ac9_identical_inputs_hash_the_same_in_a_separate_interpreter(label, env):
    """AC9: the hash is canonical across processes, not merely stable in one.

    Every other AC9 test compares two hashes produced inside a single
    interpreter, so a hash that depended on interpreter-local state would
    satisfy all of them and still hand two workers, two containers or two
    deploys different hashes for the same governed inputs. The two failure
    modes that actually cause this are exercised here:

    * ``PYTHONHASHSEED`` -- randomised per process, so anything reduced through
      a ``set`` or ``hash()`` on the way into the digest would move;
    * the ambient locale -- the canonical form contains non-ASCII governance
      and knowledge text, so encoding it with the platform default rather than
      an explicit UTF-8 encode would move the digest too.

    Both subprocesses assemble the *same* fixed inputs as the in-process call,
    through the real service, so the comparison is like for like.
    """
    in_process = _ac9_hash_probe.probe()
    out_of_process = _run_hash_probe(**env)

    assert out_of_process["context_hash"] == in_process["context_hash"], label
    assert out_of_process["input_digests"] == in_process["input_digests"], label
    assert out_of_process["assembly_version"] == in_process["assembly_version"]
    # Sanity: the probe really did hash something, and it is the canonical
    # function of the digests it published.
    assert in_process["context_hash"] == service.compute_assembly_hash(
        in_process["input_digests"]
    )
    assert len(in_process["context_hash"].removeprefix("sha256:")) == 64


def test_ac9_an_assembly_of_other_inputs_in_between_does_not_move_the_hash(client, session):
    """AC9: repeatability must survive traffic, not just back-to-back calls.

    The existing tests assemble the same inputs consecutively. Any memoisation
    or accumulated module state keyed on the wrong thing would survive that and
    only show up once a different assembly runs in between -- which is the
    normal case for a shared service.
    """
    payload = governed_request()
    other = governed_request(
        request=request_input(id="MDSU-999", title="Unrelated request"),
        repository=repository_input(commit_sha="fed9876cba5432", branch="release"),
        entry_ids=[SECOND_APPROVED_ENTRY_ID],
        governance=[governance_input(id="GOV-X", topic="observability", rule="Emit traces.")],
    )

    first = assemble_ok(client, payload)
    between = assemble_ok(client, other)
    second = assemble_ok(client, payload)

    assert second["context_hash"] == first["context_hash"]
    assert second["input_digests"] == first["input_digests"]
    # ...and the intervening assembly was genuinely a different one, so the
    # repeat above is not just two hashes of the same cached result.
    assert between["context_hash"] != first["context_hash"]


def _reorder(value):
    """Rebuild dicts with their keys in reverse order, recursively."""
    if isinstance(value, dict):
        return {key: _reorder(value[key]) for key in reversed(list(value))}
    if isinstance(value, list):
        return [_reorder(item) for item in value]
    return value


def test_ac9_the_json_key_order_of_the_request_does_not_change_the_hash(client):
    """AC9: identical governed inputs hash alike however the caller serialised them.

    Two clients (or one client across two library versions) can send the same
    governed inputs with the JSON object keys in any order. If canonicalisation
    followed insertion order instead of sorting, the hash would silently split
    into per-caller variants while every same-payload test still passed.
    """
    payload = governed_request(
        entry_ids=[APPROVED_ENTRY_ID, SECOND_APPROVED_ENTRY_ID],
        governance=[
            governance_input(id="GOV-1"),
            governance_input(id="GOV-2", topic="code-review", rule="Two approvals required."),
        ],
    )
    shuffled = _reorder(payload)

    # The reordering is real: same content, different serialisation.
    assert list(shuffled) != list(payload)
    assert list(shuffled["repository"]) != list(payload["repository"])
    assert json.dumps(shuffled, sort_keys=True) == json.dumps(payload, sort_keys=True)

    assert assemble_ok(client, shuffled)["context_hash"] == assemble_ok(client, payload)[
        "context_hash"
    ]


def test_ac9_every_entry_point_derives_the_same_hash_from_the_same_inputs(client):
    """AC9: one canonical hash per governed input set, not one per endpoint.

    Assembly, lock creation and the staleness comparison each hash the same
    inputs. If any of them hashed slightly different material, a freshly issued
    lock could read as stale immediately -- determinism has to hold across the
    entry points, not only across repeats of one of them.
    """
    payload = governed_request()

    assembled = assemble_ok(client, payload)
    lock = client.post("/api/governed-context/lock", json=payload)
    assert lock.status_code == 201, lock.text
    status_body = client.post(
        "/api/governed-context/lock/status", json={"lock": lock.json(), "current": payload}
    )
    assert status_body.status_code == 200, status_body.text
    body = status_body.json()

    assert lock.json()["context_hash"] == assembled["context_hash"]
    assert body["locked_context_hash"] == assembled["context_hash"]
    assert body["current_context_hash"] == assembled["context_hash"]
    assert lock.json()["input_digests"] == assembled["input_digests"]


# ---------------------------------------------------------------------------
# AC10 -- Relevant change detection
# ---------------------------------------------------------------------------


def test_ac10_changing_the_engineering_request_changes_the_hash(client):
    baseline = assemble_ok(client, governed_request())
    changed = assemble_ok(
        client, governed_request(request=request_input(description="A different requirement."))
    )

    assert changed["context_hash"] != baseline["context_hash"]


def test_ac10_changing_the_repository_commit_changes_the_hash(client):
    baseline = assemble_ok(client, governed_request())
    changed = assemble_ok(
        client, governed_request(repository=repository_input(commit_sha="fed9876cba5432"))
    )

    assert changed["context_hash"] != baseline["context_hash"]


def test_ac10_changing_approved_knowledge_changes_the_hash(client, session):
    baseline = assemble_ok(client, governed_request())

    added = assemble_ok(
        client, governed_request(entry_ids=[APPROVED_ENTRY_ID, SECOND_APPROVED_ENTRY_ID])
    )
    assert added["context_hash"] != baseline["context_hash"]

    session.entries = [make_entry(APPROVED_ENTRY_ID, content="Retries are now linear.")]
    edited = assemble_ok(client, governed_request())
    assert edited["context_hash"] != baseline["context_hash"]


def test_ac10_changing_governance_changes_the_hash(client):
    baseline = assemble_ok(client, governed_request())
    changed = assemble_ok(
        client,
        governed_request(
            governance=[governance_input(rule="Every migration must be tested on a replica.")]
        ),
    )

    assert changed["context_hash"] != baseline["context_hash"]


def test_ac10_irrelevant_repository_metadata_still_participates(client):
    """Branch is governed source material, so changing it must move the hash."""
    baseline = assemble_ok(client, governed_request())
    changed = assemble_ok(client, governed_request(repository=repository_input(branch="release")))

    assert changed["context_hash"] != baseline["context_hash"]


# ---------------------------------------------------------------------------
# AC11 -- Context lock staleness
# ---------------------------------------------------------------------------


def lock_status(client, lock: dict, current: dict):
    return client.post(
        "/api/governed-context/lock/status", json={"lock": lock, "current": current}
    )


def test_ac11_unchanged_inputs_leave_the_lock_fresh(client):
    payload = governed_request()
    lock = client.post("/api/governed-context/lock", json=payload).json()

    response = lock_status(client, lock, payload)
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["stale"] is False
    assert body["reasons"] == []
    assert body["locked_context_hash"] == body["current_context_hash"] == lock["context_hash"]


@pytest.mark.parametrize(
    ("section", "mutate"),
    [
        ("requirement_context", lambda p: p.update(request=request_input(title="Something else"))),
        (
            "repository_context",
            lambda p: p.update(repository=repository_input(commit_sha="fed9876cba5432")),
        ),
        ("knowledge_context", lambda p: p.update(knowledge={"entry_ids": []})),
        ("governance_context", lambda p: p.update(governance=[])),
    ],
)
def test_ac11_changed_governed_inputs_mark_the_lock_stale(client, section, mutate):
    payload = governed_request()
    lock = client.post("/api/governed-context/lock", json=payload).json()

    changed = governed_request()
    mutate(changed)

    body = lock_status(client, lock, changed).json()

    assert body["stale"] is True
    assert body["locked_context_hash"] != body["current_context_hash"]
    reasons = {reason["section"]: reason for reason in body["reasons"]}
    assert section in reasons
    assert reasons[section]["locked_digest"] != reasons[section]["current_digest"]
    assert reasons[section]["reason"]


def test_ac11_staleness_reports_every_changed_section(client):
    payload = governed_request()
    lock = client.post("/api/governed-context/lock", json=payload).json()

    changed = governed_request(
        request=request_input(title="Something else"),
        repository=repository_input(commit_sha="fed9876cba5432"),
        entry_ids=[],
        governance=[],
    )

    body = lock_status(client, lock, changed).json()

    assert {reason["section"] for reason in body["reasons"]} == {
        "requirement_context",
        "repository_context",
        "knowledge_context",
        "governance_context",
    }


GOVERNED_SECTIONS = (
    "requirement_context",
    "repository_context",
    "knowledge_context",
    "governance_context",
)

# The governed input each section digest is the fingerprint of, named the way
# AC11 names it ("changed requirement/repository/knowledge/governance").
SECTION_KEYWORD = {
    "requirement_context": "request",
    "repository_context": "repository",
    "knowledge_context": "knowledge",
    "governance_context": "governance",
}

# ``governed_inputs`` is the field AC11 says the check compares. It is a second
# projection of the same governed inputs the section digests fingerprint.
SECTION_TO_GOVERNED_INPUT = {
    "requirement_context": "request_digest",
    "repository_context": "repository_digest",
    "governance_context": "governance_digest",
}


def assemble_in_process(payload: dict, entries: list[Entry] | None = None):
    """Build an assembly through the real services, without the HTTP layer."""
    from app.schemas.context_assembly import GovernedContextRequest

    parsed = GovernedContextRequest.model_validate(payload)
    seeded = entries if entries is not None else [
        make_entry(APPROVED_ENTRY_ID),
        make_entry(SECOND_APPROVED_ENTRY_ID),
    ]
    selected = asyncio.run(
        knowledge_context.select_approved_entries(
            StubSession(seeded), payload["knowledge"]["entry_ids"]
        )
    )
    return service.assemble_governed_context(
        service.build_requirement_context(parsed.request),
        service.build_repository_context(parsed.repository),
        service.build_knowledge_context(selected),
        service.build_governance_context(parsed.governance),
    )


def reasons_by_section(body: dict) -> dict[str, dict]:
    reasons = body["reasons"]
    sections = [reason["section"] for reason in reasons]
    assert len(sections) == len(set(sections)), f"a section was reported twice: {sections}"
    return {reason["section"]: reason for reason in reasons}


def test_ac11_the_digests_the_check_compares_are_the_governed_inputs_the_lock_records():
    """AC11 is worded against ``lock.governed_inputs``; the check reads ``input_digests``.

    Those two lock fields are built from one assembly, so today they agree and
    the check really is comparing the recorded governed inputs. Nothing asserted
    that, though — so if ``lock_assembly`` ever recorded provenance from one
    place and digests from another, ``governed_inputs`` would become decorative
    and every staleness verdict would silently be about something else. Pinned
    here across four differently-shaped assemblies rather than one.
    """
    payloads = [
        governed_request(),
        governed_request(entry_ids=[]),
        governed_request(governance=[]),
        governed_request(
            request=request_input(id=None, source="github"),
            repository=repository_input(branch="release", commit_sha="0badc0ffee1234"),
            entry_ids=[APPROVED_ENTRY_ID, SECOND_APPROVED_ENTRY_ID],
        ),
    ]

    for payload in payloads:
        assembly = assemble_in_process(payload)
        lock = service.lock_assembly(assembly)

        for section, field in SECTION_TO_GOVERNED_INPUT.items():
            assert lock.input_digests[section] == getattr(lock.governed_inputs, field), (
                f"{section} digest and governed_inputs.{field} disagree; the staleness "
                "check would no longer be comparing the recorded governed inputs"
            )
        # Knowledge keeps its own inner hash, which the section digest covers.
        assert lock.governed_inputs.knowledge_hash == assembly.knowledge_context.knowledge_hash
        assert lock.governed_inputs.knowledge_entry_ids == list(
            assembly.knowledge_context.entry_ids
        )
        assert lock.governed_inputs.repository_commit_sha == assembly.repository_context.commit_sha
        assert set(lock.input_digests) == set(GOVERNED_SECTIONS)


def test_ac11_every_governed_section_has_its_own_staleness_reason():
    """AC11 requires a reason per changed input, for all four governed inputs.

    A section that is hashed into the context but missing from the reason table
    would still flip ``stale``, via the ``assembly`` fallback — but the answer
    would no longer say *what* changed, which is the half of AC11 the fallback
    cannot satisfy. Derived from the real digest keys so a fifth governed
    section cannot be added without a reason for it.
    """
    digest_keys = set(assemble_in_process(governed_request()).input_digests)

    assert digest_keys == set(GOVERNED_SECTIONS)
    assert set(service._STALENESS_REASONS) == digest_keys
    messages = list(service._STALENESS_REASONS.values())
    assert len(set(messages)) == len(messages), "two sections share one reason; ambiguous"
    for section, keyword in SECTION_KEYWORD.items():
        assert keyword in service._STALENESS_REASONS[section].lower()


@pytest.mark.parametrize(
    ("section", "current"),
    [
        pytest.param(
            "requirement_context",
            governed_request(request=request_input(description="A different requirement.")),
            id="requirement-source",
        ),
        pytest.param(
            "repository_context",
            governed_request(repository=repository_input(commit_sha="fed9876cba5432")),
            id="repository-commit",
        ),
        pytest.param(
            "knowledge_context",
            governed_request(entry_ids=[SECOND_APPROVED_ENTRY_ID]),
            id="approved-knowledge",
        ),
        pytest.param(
            "governance_context",
            governed_request(governance=[governance_input(rule="Never skip a review.")]),
            id="governance-inputs",
        ),
    ],
)
def test_ac11_one_changed_input_is_reported_as_exactly_that_input(client, section, current):
    """AC11: the reason must *identify* the changed input, not just flag staleness.

    ``test_ac11_changed_governed_inputs_mark_the_lock_stale`` asserts the
    expected section is present, which an implementation that reported all four
    sections on any change would also pass. This asserts the other three are
    absent, and that their digests were genuinely carried over unchanged — so
    the verdict is per governed input.
    """
    payload = governed_request()
    lock = lock_ok(client, payload)

    response = lock_status(client, lock, current)
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["stale"] is True
    assert body["lock_id"] == lock["lock_id"]
    reasons = reasons_by_section(body)
    assert set(reasons) == {section}, f"expected only {section} to be stale"

    reason = reasons[section]
    assert reason["locked_digest"] == lock["input_digests"][section]
    assert reason["current_digest"] != reason["locked_digest"]
    assert SECTION_KEYWORD[section] in reason["reason"].lower()

    unchanged = [other for other in GOVERNED_SECTIONS if other != section]
    fresh = lock_status(client, lock, payload).json()
    assert fresh["stale"] is False
    for other in unchanged:
        assert other not in reasons


def test_ac11_a_changed_commit_is_reported_against_the_commit_the_lock_recorded(client):
    """The AC11 worked example: lock, move the repository commit, re-check.

    Asserts the provenance side too — the answer is stale *because* the commit
    the lock recorded is no longer the current one, and checking a lock never
    rewrites the commit it was issued against.
    """
    payload = governed_request()
    lock = lock_ok(client, payload)
    assert lock["governed_inputs"]["repository_commit_sha"] == "abc1234def5678"

    current = governed_request(repository=repository_input(commit_sha="fed9876cba5432"))
    body = lock_status(client, lock, current).json()

    assert body["stale"] is True
    reasons = reasons_by_section(body)
    assert set(reasons) == {"repository_context"}
    assert reasons["repository_context"]["locked_digest"] == (
        lock["governed_inputs"]["repository_digest"]
    )
    assert (
        lock["governed_inputs"]["repository_commit_sha"]
        != current["repository"]["commit_sha"]
    )
    # The lock is an input to the check, never an output of it.
    assert lock_ok(client, payload)["governed_inputs"] == lock["governed_inputs"]


def test_ac11_editing_approved_knowledge_in_place_makes_the_lock_stale(session, client):
    """AC11 compares against *current source state*, not against the request body.

    Every other staleness test changes the submitted inputs. Here the submitted
    inputs are byte-identical and the KB entry behind them moved instead, which
    is the case a request-diffing implementation would call fresh.
    """
    payload = governed_request()
    lock = lock_ok(client, payload)

    session.entries = [
        make_entry(
            APPROVED_ENTRY_ID,
            content="Ingestion retries are now linear, not exponential.",
            updated_at=datetime(2026, 8, 15, 9, 0, tzinfo=timezone.utc),
        )
    ]

    body = lock_status(client, lock, payload).json()

    assert body["stale"] is True
    reasons = reasons_by_section(body)
    assert set(reasons) == {"knowledge_context"}
    assert reasons["knowledge_context"]["locked_digest"] == (
        lock["input_digests"]["knowledge_context"]
    )
    assert body["current_context_hash"] != body["locked_context_hash"]


def test_ac11_restoring_the_source_state_makes_the_lock_fresh_again(session, client):
    """Staleness is a live comparison, not a latch set by the first drift."""
    payload = governed_request()
    lock = lock_ok(client, payload)

    session.entries = [make_entry(APPROVED_ENTRY_ID, content="Temporarily rewritten.")]
    assert lock_status(client, lock, payload).json()["stale"] is True

    session.entries = [make_entry(APPROVED_ENTRY_ID)]
    restored = lock_status(client, lock, payload).json()

    assert restored["stale"] is False
    assert restored["reasons"] == []
    assert restored["current_context_hash"] == lock["context_hash"]


def test_ac11_staleness_is_driven_by_inputs_not_by_age_or_identity(client):
    """A lock does not expire, and is not stale merely for being an old copy."""
    payload = governed_request()
    lock = lock_ok(client, payload)

    aged = dict(
        lock,
        created_at=(
            datetime.fromisoformat(lock["created_at"]) - timedelta(days=400)
        ).isoformat(),
    )
    body = lock_status(client, aged, payload).json()

    assert body["stale"] is False
    assert body["reasons"] == []
    assert body["lock_id"] == lock["lock_id"]


def test_ac11_a_lock_recording_no_digests_is_never_reported_fresh(client):
    """A lock that carries no governed-input fingerprints cannot be vouched for.

    ``input_digests`` defaults to ``{}``, so a hand-built or truncated lock can
    reach the endpoint with nothing to compare. It must fail closed.
    """
    payload = governed_request()
    lock = lock_ok(client, payload)

    body = lock_status(client, dict(lock, input_digests={}), payload).json()

    assert body["stale"] is True
    assert set(reasons_by_section(body)) == set(GOVERNED_SECTIONS)
    for reason in body["reasons"]:
        assert reason["locked_digest"] is None
        assert reason["current_digest"]


def test_ac11_a_context_hash_that_no_longer_matches_is_stale_on_its_own(client):
    """The section-by-section compare is backstopped by the context hash.

    If a lock's hash and its section digests disagree, the lock is internally
    inconsistent; answering "fresh" would hand downstream a hash that no
    assembly of the current inputs produces.
    """
    payload = governed_request()
    lock = lock_ok(client, payload)
    tampered = dict(lock, context_hash="sha256:" + "0" * 64)

    body = lock_status(client, tampered, payload).json()

    assert body["stale"] is True
    reasons = reasons_by_section(body)
    assert set(reasons) == {"assembly"}
    assert reasons["assembly"]["locked_digest"] == tampered["context_hash"]
    assert reasons["assembly"]["current_digest"] == lock["context_hash"]
    assert body["locked_context_hash"] != body["current_context_hash"]


@pytest.mark.parametrize(
    ("current", "expected_status"),
    [
        pytest.param(
            governed_request(
                governance=[
                    governance_input(id="GOV-A", rule="Migrations must be reversible."),
                    governance_input(id="GOV-B", rule="Migrations may be irreversible."),
                ]
            ),
            409,
            id="conflicting-governance",
        ),
        pytest.param(governed_request(entry_ids=[UNAPPROVED_ENTRY_ID]), 400, id="unapproved-knowledge"),
        pytest.param(governed_request(entry_ids=[MISSING_ENTRY_ID]), 404, id="unknown-knowledge"),
        pytest.param(governed_request(request=request_input(description="   ")), 422, id="invalid-request"),
    ],
)
def test_ac11_a_current_state_that_cannot_be_assembled_yields_no_verdict(
    client, current, expected_status
):
    """AC11 answers against a valid current assembly or not at all.

    "Fresh" from an unassemblable current state would be the silent acceptance
    AC4/AC5/AC12 exist to prevent, arriving through the staleness door.
    """
    lock = lock_ok(client, governed_request())

    response = lock_status(client, lock, current)

    assert response.status_code == expected_status, response.text
    assert "stale" not in response.json()


def test_ac11_the_frontend_staleness_contract_matches_the_backend():
    """The staleness verdict is typed by hand in the browser; drift is silent.

    Same reasoning as the AC7 lock-contract check: the frontend service test
    asserts against hand-written fixtures shaped by these types, so a rename on
    either side keeps both suites green while the wire contract breaks.
    """
    contract = (
        Path(__file__).resolve().parents[2] / "frontend/src/types/governedContext.ts"
    )
    if not contract.exists():  # backend-only checkout
        pytest.skip("frontend contract file is not present in this checkout")
    source = contract.read_text(encoding="utf-8")

    def declared_fields(type_name: str) -> set[str]:
        block = re.search(rf"export type {type_name} = \{{\n(.*?)\n\}}", source, re.DOTALL)
        assert block, f"{type_name} is no longer declared in {contract.name}"
        return set(re.findall(r"^  (\w+)\??:", block.group(1), re.MULTILINE))

    from app.schemas.context_assembly import LockStatusResponse, StalenessReason

    assert declared_fields("StalenessReason") == set(StalenessReason.model_fields)
    assert declared_fields("LockStatusResponse") == set(LockStatusResponse.model_fields)


# ---------------------------------------------------------------------------
# AC12 -- Governance conflicts never yield an apparently valid assembly
# ---------------------------------------------------------------------------


def test_ac12_conflicting_governance_blocks_the_whole_assembly(client):
    payload = governed_request(
        governance=[
            governance_input(id="GOV-A", rule="Migrations must be reversible."),
            governance_input(id="GOV-B", rule="Migrations may be irreversible."),
        ]
    )

    for path in ("/api/governed-context/assemble", "/api/governed-context/lock"):
        response = client.post(path, json=payload)
        assert response.status_code == 409, path
        assert "context_hash" not in response.json()


# ---------------------------------------------------------------------------
# MDSU-325 downstream retrieval contract
# ---------------------------------------------------------------------------

def test_mdsu325_persisted_lock_can_be_retrieved_by_id(client):
    payload = governed_request()
    created = client.post("/api/governed-context/lock", json=payload)
    assert created.status_code == 201
    lock = created.json()

    retrieved = client.get(f"/api/governed-context/locks/{lock['lock_id']}")
    assert retrieved.status_code == 200
    body = retrieved.json()
    assert body["lock"] == lock
    assert body["governed_context"]["context_hash"] == lock["context_hash"]
    assert body["governed_context"]["repository_context"]["commit_sha"] == payload["repository"]["commit_sha"]


def test_mdsu325_persisted_lock_status_reassembles_current_governed_inputs(client):
    payload = governed_request()
    lock = client.post("/api/governed-context/lock", json=payload).json()

    status_response = client.get(f"/api/governed-context/locks/{lock['lock_id']}/status")
    assert status_response.status_code == 200
    status_body = status_response.json()
    assert status_body["lock_id"] == lock["lock_id"]
    assert status_body["stale"] is False


def test_mdsu325_unknown_persisted_lock_returns_404(client):
    response = client.get("/api/governed-context/locks/lock-does-not-exist")
    assert response.status_code == 404

# ---------------------------------------------------------------------------
# Kaiwora analysis -> KB governed lock handoff
# ---------------------------------------------------------------------------

def kaiwora_analysis_request(**overrides):
    payload = {
        "analysis_source": "kaiwora",
        "analysis_id": "analysis-mdsu326",
        "analysis_hash": "sha256:" + "a" * 64,
        "requirement_analysis": {
            "request_id": "MDSU-326",
            "title": "John runtime integration",
            "description": "Integrate governed John runtime controls into Kaiwora.",
            "acceptance_criteria": ["Runtime controls are integrated and verifiable."],
            "clarified_requirement": "Add John runtime controls without bypassing Project Run governance.",
            "constraints": ["Preserve existing Project Run behaviour."],
            "assumptions": ["Existing execution engine remains authoritative after the lock."],
            "ambiguities": [],
            "dependencies": ["MDSU-325"],
            "source": "jira:MDSU-326",
        },
        "repository_analysis": {
            "name": "Agent_panel",
            "url": "https://github.com/Luminar-Consulting-Org/Agent_panel",
            "branch": "develop",
            "commit_sha": "abc1234def5678",
            "relevant_files": [
                {"path": "agent_core/app/routers/runs.py", "language": "python", "role": "agent_core"},
                {"path": "agent_core/runner/agent_runner/run.py", "language": "python", "role": "agent_core"},
            ],
            "impacted_components": ["agent_core"],
            "dependencies": ["Project Run"],
            "architecture_context": ["Project Run is the governed execution entry point."],
            "analysis_evidence": ["indexed_files=200", "relevant_files=2"],
        },
        "knowledge": {"entry_ids": []},
        "governance": [],
    }
    payload.update(overrides)
    return payload


def test_kaiwora_analysis_can_create_reusable_governed_lock(client):
    payload = kaiwora_analysis_request()
    created = client.post("/api/governed-context/lock-from-analysis", json=payload)
    assert created.status_code == 201, created.text
    lock = created.json()
    retrieved = client.get(f"/api/governed-context/locks/{lock['lock_id']}")
    assert retrieved.status_code == 200
    body = retrieved.json()
    assert body["governed_context"]["requirement_context"]["analysis_source"] == "kaiwora"
    assert body["governed_context"]["requirement_context"]["clarified_requirement"].startswith("Add John")
    assert body["governed_context"]["repository_context"]["analysis_mode"] == "external_analysis"
    assert body["governed_context"]["repository_context"]["relevant_files"] == [
        "agent_core/app/routers/runs.py",
        "agent_core/runner/agent_runner/run.py",
    ]


def test_kaiwora_analysis_lock_is_deterministic_and_reusable(client):
    payload = kaiwora_analysis_request()
    first = client.post("/api/governed-context/lock-from-analysis", json=payload).json()
    second = client.post("/api/governed-context/lock-from-analysis", json=payload).json()
    assert first["lock_id"] == second["lock_id"]
    assert first["context_hash"] == second["context_hash"]
    status_response = client.get(f"/api/governed-context/locks/{first['lock_id']}/status")
    assert status_response.status_code == 200, status_response.text
    assert status_response.json()["stale"] is False


def test_material_kaiwora_analysis_change_creates_new_lock(client):
    first_payload = kaiwora_analysis_request()
    second_payload = kaiwora_analysis_request()
    second_payload["requirement_analysis"]["constraints"].append("John hooks must fail closed.")
    first = client.post("/api/governed-context/lock-from-analysis", json=first_payload).json()
    second = client.post("/api/governed-context/lock-from-analysis", json=second_payload).json()
    assert first["context_hash"] != second["context_hash"]
    assert first["lock_id"] != second["lock_id"]


def test_legacy_lock_contract_remains_backward_compatible_after_analysis_support(client):
    payload = governed_request()
    created = client.post("/api/governed-context/lock", json=payload)
    assert created.status_code == 201
    lock = created.json()
    status_response = client.get(f"/api/governed-context/locks/{lock['lock_id']}/status")
    assert status_response.status_code == 200
    assert status_response.json()["stale"] is False


def test_repository_file_semantics_are_preserved_in_analysis_lock(client):
    payload = kaiwora_analysis_request()
    payload["repository_analysis"]["relevant_files"] = [
        {
            "path": "price.py",
            "language": "python",
            "role": "pricing",
            "context_role": "implementation",
            "access": "read_write",
        },
        {
            "path": "tax_rules.py",
            "language": "python",
            "role": "tax",
            "context_role": "verification",
            "access": "read_only",
        },
    ]
    created = client.post("/api/governed-context/lock-from-analysis", json=payload)
    assert created.status_code == 201, created.text
    files = created.json()["governed_context"]["repository_context"]["files"]
    by_path = {item["path"]: item for item in files}
    assert by_path["price.py"]["context_role"] == "implementation"
    assert by_path["price.py"]["access"] == "read_write"
    assert by_path["tax_rules.py"]["context_role"] == "verification"
    assert by_path["tax_rules.py"]["access"] == "read_only"


def test_repository_file_access_semantics_change_context_hash(client):
    writable = kaiwora_analysis_request()
    writable["repository_analysis"]["relevant_files"] = [
        {
            "path": "tax_rules.py",
            "language": "python",
            "role": "tax",
            "context_role": "verification",
            "access": "read_write",
        }
    ]
    protected = kaiwora_analysis_request()
    protected["repository_analysis"]["relevant_files"] = [
        {
            "path": "tax_rules.py",
            "language": "python",
            "role": "tax",
            "context_role": "verification",
            "access": "read_only",
        }
    ]
    first = client.post("/api/governed-context/lock-from-analysis", json=writable)
    second = client.post("/api/governed-context/lock-from-analysis", json=protected)
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["context_hash"] != second.json()["context_hash"]
    assert first.json()["lock_id"] != second.json()["lock_id"]

# ---------------------------------------------------------------------------
# Kaiwora Cloud V5.0.1 persisted-lock compatibility + isolation regressions
# ---------------------------------------------------------------------------

def test_cloud_lock_requires_exact_scope_when_not_default(client):
    payload = kaiwora_analysis_request(
        tenant_id="tenant-a",
        workspace_id="workspace-a",
        repository_id="repository-a",
    )
    created = client.post("/api/governed-context/lock-from-analysis", json=payload)
    assert created.status_code == 201, created.text
    lock_id = created.json()["lock_id"]

    # Cloud-owned locks never fall back to the legacy unscoped contract.
    assert client.get(f"/api/governed-context/locks/{lock_id}").status_code == 404

    allowed = client.get(
        f"/api/governed-context/locks/{lock_id}",
        params={
            "tenant_id": "tenant-a",
            "workspace_id": "workspace-a",
            "repository_id": "repository-a",
        },
    )
    assert allowed.status_code == 200


def test_cloud_lock_cross_tenant_scope_is_denied(client):
    payload = kaiwora_analysis_request(
        tenant_id="tenant-a",
        workspace_id="workspace-a",
        repository_id="repository-a",
    )
    lock_id = client.post("/api/governed-context/lock-from-analysis", json=payload).json()["lock_id"]

    denied = client.get(
        f"/api/governed-context/locks/{lock_id}",
        params={
            "tenant_id": "tenant-b",
            "workspace_id": "workspace-a",
            "repository_id": "repository-a",
        },
    )
    assert denied.status_code == 404


def test_cloud_lock_partial_scope_fails_closed(client):
    payload = kaiwora_analysis_request(
        tenant_id="tenant-a",
        workspace_id="workspace-a",
        repository_id="repository-a",
    )
    lock_id = client.post("/api/governed-context/lock-from-analysis", json=payload).json()["lock_id"]
    response = client.get(
        f"/api/governed-context/locks/{lock_id}",
        params={"tenant_id": "tenant-a", "workspace_id": "workspace-a"},
    )
    assert response.status_code == 404


def test_legacy_lingyu_analysis_source_remains_read_compatible(client):
    """Legacy persisted/integration payloads remain readable; new defaults are Kaiwora."""
    payload = kaiwora_analysis_request(analysis_source="lingyu", analysis_id="analysis-legacy-lingyu")
    created = client.post("/api/governed-context/lock-from-analysis", json=payload)
    assert created.status_code == 201, created.text
    lock = created.json()
    retrieved = client.get(f"/api/governed-context/locks/{lock['lock_id']}")
    assert retrieved.status_code == 200
    assert retrieved.json()["governed_context"]["requirement_context"]["analysis_source"] == "lingyu"
