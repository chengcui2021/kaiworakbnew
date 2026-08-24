"""Fixtures for the Governed Context Assembly contract tests (MDSU-345).

Two deliberate constraints shape this file:

* ``app.main`` is not imported. These tests target the governed-context
  contract, so only that router is mounted; unrelated persistent-KB routers
  stay out of the blast radius.
* No database is required. ``select_approved_entries`` is the only DB consumer
  on this path, so a stub session standing in for ``AsyncSession`` is enough to
  exercise the real approval-enforcement code rather than mocking around it.
"""
from __future__ import annotations

import builtins
import os
import shutil
import subprocess
from contextlib import ExitStack, contextmanager
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.persistence.database import get_db
from app.persistence.models import ComponentName, Entry, EntryStatus, EntryType
from app.routes import context_assembly as context_assembly_routes

# Stable ids so digests/hashes in assertions stay reproducible.
APPROVED_ENTRY_ID = "11111111-1111-4111-8111-111111111111"
SECOND_APPROVED_ENTRY_ID = "22222222-2222-4222-8222-222222222222"
UNAPPROVED_ENTRY_ID = "33333333-3333-4333-8333-333333333333"
MISSING_ENTRY_ID = "99999999-9999-4999-8999-999999999999"


def make_entry(
    entry_id: str,
    *,
    title: str = "Retry policy for ingestion",
    content: str = "Ingestion retries use exponential backoff.",
    source: str | None = "confluence://eng/retry-policy",
    status: EntryStatus = EntryStatus.RESOLVED,
    updated_at: datetime | None = None,
) -> Entry:
    """Build a detached ``Entry`` ORM instance (never flushed to a database)."""
    return Entry(
        id=UUID(entry_id),
        title=title,
        content=content,
        source=source,
        author="qa",
        status=status,
        entry_type=EntryType.DOCUMENTATION,
        component_name=ComponentName.API,
        created_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        updated_at=updated_at or datetime(2026, 8, 1, 12, 30, tzinfo=timezone.utc),
    )


class _StubResult:
    def __init__(self, entries: list[Entry]) -> None:
        self._entries = entries

    def scalars(self) -> "_StubResult":
        return self

    def all(self) -> list[Entry]:
        return list(self._entries)


class StubSession:
    """Minimal stand-in for ``AsyncSession``.

    Returns the whole seeded row set for any query. That is behaviourally
    identical to running the real ``WHERE id IN (...)``, because
    ``select_approved_entries`` looks rows up by id itself and derives both
    "missing" and "not approved" from what it gets back — so unknown-id and
    unapproved-id handling are exercised for real, not simulated.
    """

    def __init__(self, entries: list[Entry]) -> None:
        self.entries = list(entries)
        self.statements: list[object] = []
        self.lock_rows: dict[str, object] = {}

    async def execute(self, statement: object) -> _StubResult:
        self.statements.append(statement)
        return _StubResult(self.entries)

    async def get(self, model: object, key: str):
        return self.lock_rows.get(str(key))

    def add(self, value: object) -> None:
        lock_id = str(getattr(value, "lock_id", "") or "")
        if lock_id:
            self.lock_rows[lock_id] = value

    async def commit(self) -> None:
        return None


@pytest.fixture
def kb_entries() -> list[Entry]:
    """Seeded knowledge base: two approved (resolved) entries and one open."""
    return [
        make_entry(APPROVED_ENTRY_ID),
        make_entry(
            SECOND_APPROVED_ENTRY_ID,
            title="Approved logging standard",
            content="Structured JSON logs only.",
            source="confluence://eng/logging",
        ),
        make_entry(
            UNAPPROVED_ENTRY_ID,
            title="Draft caching proposal",
            content="Unreviewed caching notes.",
            source=None,
            status=EntryStatus.OPEN,
        ),
    ]


@pytest.fixture
def session(kb_entries: list[Entry]) -> StubSession:
    return StubSession(kb_entries)


@pytest.fixture
def client(session: StubSession):
    """TestClient over a minimal app exposing only the governed-context router."""
    app = FastAPI()
    app.include_router(context_assembly_routes.router)
    app.dependency_overrides[get_db] = lambda: session
    with TestClient(app) as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# Request payload builders
# ---------------------------------------------------------------------------


def request_input(**overrides) -> dict:
    payload = {
        "id": "MDSU-345",
        "title": "Add governed context assembly",
        "description": "Combine requirement, repository, knowledge and governance context.",
        "acceptance_criteria": ["Deterministic hash", "Approved knowledge only"],
        "source": "jira",
    }
    payload.update(overrides)
    return payload


def repository_input(**overrides) -> dict:
    payload = {
        "name": "metamorphic-kb",
        "url": "https://github.com/Luminar-Consulting-Org/metamorphic-kb",
        "branch": "main",
        "commit_sha": "abc1234def5678",
        "files": [
            {"path": "backend/app/main.py", "language": "python", "role": "entrypoint"},
            {"path": "frontend/src/App.vue", "language": "vue", "role": "shell"},
        ],
    }
    payload.update(overrides)
    return payload


def governance_input(**overrides) -> dict:
    payload = {
        "id": "GOV-1",
        "title": "Migrations are reversible",
        "topic": "database-migrations",
        "rule": "Every migration must define a downgrade path.",
        "source": "engineering-handbook",
        "status": "approved",
        "precedence": 0,
    }
    payload.update(overrides)
    return payload


def governed_request(
    *,
    request: dict | None = None,
    repository: dict | None = None,
    entry_ids: list[str] | None = None,
    governance: list[dict] | None = None,
) -> dict:
    return {
        "request": request if request is not None else request_input(),
        "repository": repository if repository is not None else repository_input(),
        "knowledge": {"entry_ids": entry_ids if entry_ids is not None else [APPROVED_ENTRY_ID]},
        "governance": governance if governance is not None else [governance_input()],
    }


# ---------------------------------------------------------------------------
# AC2 guard: repository analysis must not modify the target repository
# ---------------------------------------------------------------------------


@contextmanager
def no_repository_mutation():
    """Fail loudly if the guarded block writes, deletes, or shells out.

    AC2 requires that repository analysis never modifies the target
    repository. Rather than asserting that from code review, this makes any
    mutating call raise, so the assertion is enforced at runtime.
    """
    real_open = builtins.open

    def guarded_open(file, mode="r", *args, **kwargs):
        if any(flag in mode for flag in ("w", "a", "x", "+")):
            raise AssertionError(f"repository analysis attempted to write {file!r}")
        return real_open(file, mode, *args, **kwargs)

    def forbid(name):
        def _raise(*args, **kwargs):
            raise AssertionError(f"repository analysis attempted {name}{args!r}")

        return _raise

    blocked = [
        (os, "remove"),
        (os, "unlink"),
        (os, "rename"),
        (os, "replace"),
        (os, "mkdir"),
        (os, "makedirs"),
        (os, "rmdir"),
        (shutil, "rmtree"),
        (shutil, "copy"),
        (shutil, "move"),
        (subprocess, "run"),
        (subprocess, "Popen"),
        (subprocess, "check_output"),
    ]
    with ExitStack() as stack:
        stack.enter_context(patch.object(builtins, "open", guarded_open))
        for module, attr in blocked:
            stack.enter_context(
                patch.object(module, attr, forbid(f"{module.__name__}.{attr}"))
            )
        yield
