"""Out-of-process probe for AC9 (deterministic context hash).

The in-process AC9 tests can only show that two calls *inside one interpreter*
agree. That cannot see a hash that depends on interpreter-local state --
``PYTHONHASHSEED``-dependent ``set``/``hash()`` ordering, or the ambient locale
deciding how text is encoded before it is digested. Both would look perfectly
deterministic in a single test run and then hand two workers, two containers or
two deploys different hashes for the same governed inputs.

This module owns one fixed governed input set and builds the assembly through
the real ``app.services.context_assembly`` functions. The test imports it to get
the in-process hash and runs it as a script (``python tests/_ac9_hash_probe.py``)
under varied interpreter environments to get out-of-process hashes, so both are
derived from exactly the same inputs.

Deliberately not named ``test_*``: it is a fixture asset, not a test module.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.persistence.models import (  # noqa: E402
    ComponentName,
    Entry,
    EntryStatus,
    EntryType,
)
from app.schemas.context_assembly import (  # noqa: E402
    EngineeringRequestInput,
    GovernanceRuleInput,
    RepositoryFileInput,
    RepositoryInput,
)
from app.services import context_assembly as service  # noqa: E402

# Non-ASCII text is on purpose: canonical JSON is written with
# ``ensure_ascii=False`` and encoded explicitly as UTF-8, so a hash that
# followed the ambient locale instead would diverge between environments.
UNICODE_NOTE = "Rückverfolgbarkeit / 追跡可能性 — governance note"

REQUEST = EngineeringRequestInput(
    id="MDSU-345-AC9-PROBE",
    title="Governed context assembly",
    description=f"Deterministic hash probe. {UNICODE_NOTE}",
    acceptance_criteria=["Deterministic hash", "Approved knowledge only"],
    source="jira",
)

REPOSITORY = RepositoryInput(
    name="metamorphic-kb",
    url="https://github.com/Luminar-Consulting-Org/metamorphic-kb",
    branch="main",
    commit_sha="abc1234def5678",
    files=[
        RepositoryFileInput(path="backend/app/main.py", language="python", role="entrypoint"),
        RepositoryFileInput(path="frontend/src/App.vue", language="vue", role="shell"),
    ],
)

RULES = [
    GovernanceRuleInput(
        id="GOV-1",
        title="Migrations are reversible",
        topic="database-migrations",
        rule="Every migration must define a downgrade path.",
        source="engineering-handbook",
        status="approved",
        precedence=0,
    ),
    GovernanceRuleInput(
        id="GOV-2",
        title="Traceability",
        topic="code-review",
        rule=f"Two approvals required. {UNICODE_NOTE}",
        source="engineering-handbook",
        status="approved",
        precedence=0,
    ),
]

_UPDATED_AT = datetime(2026, 8, 1, 12, 30, tzinfo=timezone.utc)
_CREATED_AT = datetime(2026, 7, 1, tzinfo=timezone.utc)


def _entry(entry_id: str, *, title: str, content: str, source: str | None) -> Entry:
    return Entry(
        id=UUID(entry_id),
        title=title,
        content=content,
        source=source,
        author="qa",
        status=EntryStatus.RESOLVED,
        entry_type=EntryType.DOCUMENTATION,
        component_name=ComponentName.API,
        created_at=_CREATED_AT,
        updated_at=_UPDATED_AT,
    )


def entries() -> list[Entry]:
    """Fresh ORM instances every call, so identity can never carry a hash."""
    return [
        _entry(
            "22222222-2222-4222-8222-222222222222",
            title="Approved logging standard",
            content=f"Structured JSON logs only. {UNICODE_NOTE}",
            source="confluence://eng/logging",
        ),
        _entry(
            "11111111-1111-4111-8111-111111111111",
            title="Retry policy for ingestion",
            content="Ingestion retries use exponential backoff.",
            source="confluence://eng/retry-policy",
        ),
    ]


def probe() -> dict:
    """Assemble the fixed governed inputs and report only hashed material."""
    assembly = service.assemble_governed_context(
        service.build_requirement_context(REQUEST),
        service.build_repository_context(REPOSITORY),
        service.build_knowledge_context(entries()),
        service.build_governance_context(RULES),
    )
    return {
        "context_hash": assembly.context_hash,
        "input_digests": dict(assembly.input_digests),
        "assembly_version": assembly.assembly_version,
    }


if __name__ == "__main__":
    print(json.dumps(probe(), sort_keys=True))
