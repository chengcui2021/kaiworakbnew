"""Governed Context Assembly (Phase 1).

Builds the four governed context sections, combines them into one Governed
Context Assembly with a deterministic canonical hash, converts a successful
assembly into a Context Assembly Lock, and detects when an existing lock has
gone stale because governed source inputs changed.

Every function here is pure: no filesystem access, no repository mutation,
and no wall-clock value ever feeds a hash.
"""
from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import datetime, timezone

from app.persistence.models import Entry
from app.schemas.context_assembly import (
    ContextAssemblyLock,
    EngineeringGovernanceContext,
    EngineeringRequestInput,
    GovernanceConflict,
    GovernanceRuleContext,
    GovernanceRuleInput,
    GovernanceSupersession,
    GovernedContextAssembly,
    GovernedInputsRef,
    KnowledgeContext,
    KnowledgeProvenance,
    KnowledgeResolution,
    KnowledgeSnapshot,
    LockStatusResponse,
    RepositoryAnalysisContext,
    RepositoryAnalysisInput,
    RepositoryFileContext,
    RepositoryInput,
    RequirementAnalysisContext,
    RequirementAnalysisInput,
    StalenessReason,
)
from app.services.knowledge_context import (
    APPROVED_ENTRY_STATUS,
    compute_entry_context_hash,
    sha256_digest,
)

GOVERNED_ASSEMBLY_VERSION = "1"
KNOWLEDGE_SOURCE_CAPABILITY = "knowledge_context_assembly"
REPOSITORY_ANALYSIS_MODE = "read_only_metadata"
APPROVED_GOVERNANCE_STATUS = "approved"

_COMMIT_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,64}$")

_SECTION_REQUIREMENT = "requirement_context"
_SECTION_REPOSITORY = "repository_context"
_SECTION_KNOWLEDGE = "knowledge_context"
_SECTION_GOVERNANCE = "governance_context"


class RequirementValidationError(Exception):
    """Raised when the engineering request is empty or unusable."""


class RepositoryValidationError(Exception):
    """Raised when supplied repository information is unusable."""


class GovernanceConflictError(Exception):
    """Raised when governance inputs cannot be resolved deterministically."""

    def __init__(self, conflicts: list[GovernanceConflict]) -> None:
        self.conflicts = conflicts
        topics = ", ".join(sorted({c.topic for c in conflicts}))
        super().__init__(f"Conflicting governance inputs for: {topics}")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize(value: str) -> str:
    return " ".join(value.split()).casefold()


# ---------------------------------------------------------------------------
# AC1 -- Requirement Analysis Context
# ---------------------------------------------------------------------------


def build_requirement_context(payload: EngineeringRequestInput) -> RequirementAnalysisContext:
    """Structure the originating request; reject empty/whitespace-only input."""
    title = payload.title.strip()
    description = payload.description.strip()
    if not title:
        raise RequirementValidationError("request.title must not be empty or whitespace-only")
    if not description:
        raise RequirementValidationError(
            "request.description must not be empty or whitespace-only"
        )

    criteria = [c.strip() for c in payload.acceptance_criteria if c.strip()]
    request_id = (payload.id or "").strip() or None
    source = (payload.source or "").strip() or None

    digest = sha256_digest(
        {
            "request_id": request_id,
            "title": title,
            "description": description,
            "acceptance_criteria": criteria,
            "source": source,
        }
    )
    return RequirementAnalysisContext(
        request_id=request_id,
        title=title,
        description=description,
        acceptance_criteria=criteria,
        source=source,
        digest=digest,
    )


def _clean_list(values: Sequence[str]) -> list[str]:
    out: list[str] = []
    for value in values or []:
        cleaned = str(value or "").strip()
        if cleaned and cleaned not in out:
            out.append(cleaned)
    return out


def build_requirement_context_from_analysis(
    payload: RequirementAnalysisInput,
    *,
    analysis_source: str = "lingyu",
    analysis_id: str | None = None,
    analysis_hash: str | None = None,
) -> RequirementAnalysisContext:
    """Freeze externally-produced requirement intelligence without reinterpreting it."""
    title = payload.title.strip()
    description = payload.description.strip()
    if not title:
        raise RequirementValidationError("requirement_analysis.title must not be empty")
    if not description:
        raise RequirementValidationError("requirement_analysis.description must not be empty")
    data = {
        "request_id": (payload.request_id or "").strip() or None,
        "title": title,
        "description": description,
        "acceptance_criteria": _clean_list(payload.acceptance_criteria),
        "clarified_requirement": (payload.clarified_requirement or "").strip() or None,
        "constraints": _clean_list(payload.constraints),
        "assumptions": _clean_list(payload.assumptions),
        "ambiguities": _clean_list(payload.ambiguities),
        "dependencies": _clean_list(payload.dependencies),
        "analysis_source": (analysis_source or "lingyu").strip(),
        "analysis_id": (analysis_id or "").strip() or None,
        "analysis_hash": (analysis_hash or "").strip() or None,
        "source": (payload.source or "").strip() or None,
    }
    digest_data = {k: v for k, v in data.items() if k != "analysis_id"}
    return RequirementAnalysisContext(**data, digest=sha256_digest(digest_data))


def build_repository_context_from_analysis(
    payload: RepositoryAnalysisInput,
    *,
    analysis_source: str = "lingyu",
    analysis_id: str | None = None,
    analysis_hash: str | None = None,
) -> RepositoryAnalysisContext:
    """Freeze LingYu repository understanding at the analysed commit SHA."""
    name = payload.name.strip()
    commit_sha = payload.commit_sha.strip().lower()
    if not name:
        raise RepositoryValidationError("repository_analysis.name must not be empty")
    if not _COMMIT_SHA_RE.match(commit_sha):
        raise RepositoryValidationError(
            "repository_analysis.commit_sha must be a 7-64 character hexadecimal commit id"
        )
    files: list[RepositoryFileContext] = []
    seen: set[str] = set()
    for item in payload.relevant_files:
        path = item.path.strip()
        if path.startswith("./"):
            path = path[2:]
        if not path or path in seen:
            continue
        seen.add(path)
        files.append(RepositoryFileContext(
            path=path,
            language=(item.language or "").strip() or None,
            role=(item.role or "").strip() or None,
        ))
    files.sort(key=lambda x: x.path)
    source = (analysis_source or "lingyu").strip()
    data = {
        "name": name,
        "url": (payload.url or "").strip() or None,
        "branch": (payload.branch or "").strip() or None,
        "commit_sha": commit_sha,
        "file_count": len(files),
        "languages": sorted({f.language for f in files if f.language}),
        "top_level_paths": sorted({f.path.split("/", 1)[0] for f in files}),
        "files": [f.model_dump() for f in files],
        "relevant_files": [f.path for f in files],
        "impacted_components": _clean_list(payload.impacted_components),
        "dependencies": _clean_list(payload.dependencies),
        "architecture_context": _clean_list(payload.architecture_context),
        "analysis_evidence": _clean_list(payload.analysis_evidence),
        "analysis_source": source,
        "analysis_id": (analysis_id or "").strip() or None,
        "analysis_hash": (analysis_hash or "").strip() or None,
        "analysis_mode": "external_analysis",
        "read_only": True,
    }
    digest_data = {k: v for k, v in data.items() if k != "analysis_id"}
    return RepositoryAnalysisContext(**data, digest=sha256_digest(digest_data))


# ---------------------------------------------------------------------------
# AC2 -- Repository Analysis Context (metadata only, never mutates the repo)
# ---------------------------------------------------------------------------


def build_repository_context(payload: RepositoryInput) -> RepositoryAnalysisContext:
    """Structure supplied repository information without touching the repository."""
    name = payload.name.strip()
    commit_sha = payload.commit_sha.strip()
    if not name:
        raise RepositoryValidationError("repository.name must not be empty or whitespace-only")
    if not _COMMIT_SHA_RE.match(commit_sha):
        raise RepositoryValidationError(
            "repository.commit_sha must be a 7-64 character hexadecimal commit id"
        )

    files: list[RepositoryFileContext] = []
    seen_paths: set[str] = set()
    for item in payload.files:
        # Strip a leading "./" prefix only. str.lstrip("./") would strip the
        # characters, silently turning ".github/workflows/ci.yml" into
        # "github/workflows/ci.yml" and corrupting repository lineage.
        path = item.path.strip()
        if path.startswith("./"):
            path = path[2:]
        if not path or path in seen_paths:
            continue
        seen_paths.add(path)
        files.append(
            RepositoryFileContext(
                path=path,
                language=(item.language or "").strip() or None,
                role=(item.role or "").strip() or None,
            )
        )
    files.sort(key=lambda f: f.path)

    languages = sorted({f.language for f in files if f.language})
    top_level = sorted({f.path.split("/", 1)[0] for f in files})

    digest = sha256_digest(
        {
            "name": name,
            "url": (payload.url or "").strip() or None,
            "branch": (payload.branch or "").strip() or None,
            "commit_sha": commit_sha.lower(),
            "files": [
                {"path": f.path, "language": f.language, "role": f.role} for f in files
            ],
            "analysis_mode": REPOSITORY_ANALYSIS_MODE,
        }
    )
    return RepositoryAnalysisContext(
        name=name,
        url=(payload.url or "").strip() or None,
        branch=(payload.branch or "").strip() or None,
        commit_sha=commit_sha,
        file_count=len(files),
        languages=languages,
        top_level_paths=top_level,
        files=files,
        analysis_mode=REPOSITORY_ANALYSIS_MODE,
        read_only=True,
        digest=digest,
    )


# ---------------------------------------------------------------------------
# AC3/AC4/AC8 -- Knowledge Context, reusing Knowledge Context Assembly
# ---------------------------------------------------------------------------


def build_knowledge_context(
    entries: Sequence[Entry],
    resolution: KnowledgeResolution | None = None,
) -> KnowledgeContext:
    """Wrap approved KB entries with provenance and the shared knowledge hash.

    ``entries`` must already have passed
    :func:`app.services.knowledge_context.select_approved_entries`, which is
    the same approved-knowledge gate Context Packages use.
    """
    ordered = sorted(entries, key=lambda e: str(e.id))
    provenance = [
        KnowledgeProvenance(
            entry_id=str(e.id),
            title=e.title,
            source=e.source,
            version=e.updated_at.isoformat() if e.updated_at else None,
            updated_at=e.updated_at.isoformat() if e.updated_at else None,
            status=e.status.value,
        )
        for e in ordered
    ]
    snapshots = [
        KnowledgeSnapshot(
            entry_id=str(e.id),
            title=e.title,
            content=e.content,
            source=e.source,
            version=e.updated_at.isoformat() if e.updated_at else None,
            updated_at=e.updated_at.isoformat() if e.updated_at else None,
            status=e.status.value,
        )
        for e in ordered
    ]
    knowledge_hash = compute_entry_context_hash(ordered)
    digest_payload = {
        "source_capability": KNOWLEDGE_SOURCE_CAPABILITY,
        "approved_status": APPROVED_ENTRY_STATUS.value,
        "knowledge_hash": knowledge_hash,
        "provenance": [
            {"entry_id": p.entry_id, "version": p.version} for p in provenance
        ],
        # Bind the snapshot identity to the context digest without hashing the
        # full body twice; knowledge_hash already covers {id, content}.
        "snapshot_entry_ids": [item.entry_id for item in snapshots],
    }
    # Preserve the exact legacy digest for explicit selections. Automatic
    # resolution adds its own immutable evidence only when it is actually used.
    if resolution is not None:
        digest_payload["resolution_hash"] = resolution.resolution_hash
        digest_payload["resolver_version"] = resolution.resolver_version
    digest = sha256_digest(digest_payload)
    return KnowledgeContext(
        source_capability=KNOWLEDGE_SOURCE_CAPABILITY,
        approved_status=APPROVED_ENTRY_STATUS.value,
        entry_ids=[p.entry_id for p in provenance],
        entry_count=len(provenance),
        provenance=provenance,
        snapshots=snapshots,
        resolution=resolution,
        knowledge_hash=knowledge_hash,
        digest=digest,
    )


# ---------------------------------------------------------------------------
# AC5/AC12 -- Engineering Governance Context with conflict detection
# ---------------------------------------------------------------------------


def build_governance_context(
    rules: Sequence[GovernanceRuleInput],
) -> EngineeringGovernanceContext:
    """Select applicable approved governance, detecting unresolvable conflicts.

    Rules that are not approved are excluded rather than silently accepted.
    Two approved rules on the same topic that state different things are
    resolved only when one has strictly higher precedence; otherwise the
    conflict is raised so no apparently valid assembly can be produced.
    """
    excluded: list[str] = []
    applicable: list[GovernanceRuleInput] = []
    for rule in rules:
        if (rule.status or "").strip().casefold() != APPROVED_GOVERNANCE_STATUS:
            excluded.append(rule.id)
        else:
            applicable.append(rule)

    by_topic: dict[str, list[GovernanceRuleInput]] = {}
    for rule in applicable:
        by_topic.setdefault(_normalize(rule.topic), []).append(rule)

    selected: list[GovernanceRuleContext] = []
    superseded: list[GovernanceSupersession] = []
    conflicts: list[GovernanceConflict] = []

    for topic_key in sorted(by_topic):
        group = by_topic[topic_key]
        statements = {_normalize(r.rule) for r in group}
        if len(statements) == 1:
            # Same statement, possibly duplicated across sources: keep one.
            winner = sorted(group, key=lambda r: (-r.precedence, r.id))[0]
            selected.append(_to_rule_context(winner))
            continue

        top_precedence = max(r.precedence for r in group)
        top_rules = [r for r in group if r.precedence == top_precedence]
        if len({_normalize(r.rule) for r in top_rules}) > 1:
            conflicts.append(
                GovernanceConflict(
                    topic=group[0].topic,
                    rule_ids=sorted(r.id for r in top_rules),
                    reason=(
                        "Multiple approved governance rules on this topic state "
                        f"different requirements at the same precedence ({top_precedence}); "
                        "the conflict cannot be resolved deterministically."
                    ),
                )
            )
            continue

        winner = top_rules[0]
        selected.append(_to_rule_context(winner))
        superseded.extend(
            GovernanceSupersession(
                topic=group[0].topic,
                superseded_rule_id=other.id,
                superseded_by_rule_id=winner.id,
            )
            for other in sorted(group, key=lambda r: r.id)
            if other.id != winner.id
        )

    if conflicts:
        raise GovernanceConflictError(sorted(conflicts, key=lambda c: c.topic))

    selected.sort(key=lambda r: (_normalize(r.topic), r.id))
    superseded.sort(key=lambda s: (_normalize(s.topic), s.superseded_rule_id))
    excluded.sort()

    digest = sha256_digest(
        {
            "rules": [
                {
                    "id": r.id,
                    "topic": r.topic,
                    "rule": r.rule,
                    "precedence": r.precedence,
                    "source": r.source,
                }
                for r in selected
            ],
            "excluded_rule_ids": excluded,
            "superseded": [
                {
                    "superseded_rule_id": s.superseded_rule_id,
                    "superseded_by_rule_id": s.superseded_by_rule_id,
                }
                for s in superseded
            ],
        }
    )
    return EngineeringGovernanceContext(
        rules=selected,
        excluded_rule_ids=excluded,
        superseded=superseded,
        digest=digest,
    )


def _to_rule_context(rule: GovernanceRuleInput) -> GovernanceRuleContext:
    return GovernanceRuleContext(
        id=rule.id,
        title=rule.title.strip(),
        topic=rule.topic.strip(),
        rule=rule.rule.strip(),
        source=(rule.source or "").strip() or None,
        precedence=rule.precedence,
    )


# ---------------------------------------------------------------------------
# AC6/AC9 -- Integrated assembly with a deterministic canonical hash
# ---------------------------------------------------------------------------


def section_digests(
    requirement: RequirementAnalysisContext,
    repository: RepositoryAnalysisContext,
    knowledge: KnowledgeContext,
    governance: EngineeringGovernanceContext,
) -> dict[str, str]:
    return {
        _SECTION_REQUIREMENT: requirement.digest,
        _SECTION_REPOSITORY: repository.digest,
        _SECTION_KNOWLEDGE: knowledge.digest,
        _SECTION_GOVERNANCE: governance.digest,
    }


def compute_assembly_hash(digests: dict[str, str]) -> str:
    """Canonical hash over the section digests only -- never over timestamps."""
    return sha256_digest({"version": GOVERNED_ASSEMBLY_VERSION, "sections": digests})


def assemble_governed_context(
    requirement: RequirementAnalysisContext,
    repository: RepositoryAnalysisContext,
    knowledge: KnowledgeContext,
    governance: EngineeringGovernanceContext,
) -> GovernedContextAssembly:
    digests = section_digests(requirement, repository, knowledge, governance)
    return GovernedContextAssembly(
        assembly_version=GOVERNED_ASSEMBLY_VERSION,
        requirement_context=requirement,
        repository_context=repository,
        knowledge_context=knowledge,
        governance_context=governance,
        input_digests=digests,
        context_hash=compute_assembly_hash(digests),
        created_at=_now(),
    )


# ---------------------------------------------------------------------------
# AC7/AC11 -- Context Assembly Lock and staleness
# ---------------------------------------------------------------------------


def lock_assembly(assembly: GovernedContextAssembly) -> ContextAssemblyLock:
    """Freeze an assembly into a lock that identifies its governed inputs."""
    governed_inputs = GovernedInputsRef(
        request_id=assembly.requirement_context.request_id,
        request_digest=assembly.requirement_context.digest,
        repository_commit_sha=assembly.repository_context.commit_sha,
        repository_digest=assembly.repository_context.digest,
        knowledge_entry_ids=list(assembly.knowledge_context.entry_ids),
        knowledge_hash=assembly.knowledge_context.knowledge_hash,
        governance_rule_ids=[r.id for r in assembly.governance_context.rules],
        governance_digest=assembly.governance_context.digest,
    )
    # Derived from the context hash so the same governed inputs always yield
    # the same lock identity.
    lock_id = f"lock-{assembly.context_hash.removeprefix('sha256:')[:16]}"
    return ContextAssemblyLock(
        lock_id=lock_id,
        assembly_version=assembly.assembly_version,
        context_hash=assembly.context_hash,
        input_digests=dict(assembly.input_digests),
        governed_inputs=governed_inputs,
        created_at=_now(),
    )


_STALENESS_REASONS = {
    _SECTION_REQUIREMENT: "Engineering request/source changed since the lock was created",
    _SECTION_REPOSITORY: "Repository source material changed since the lock was created",
    _SECTION_KNOWLEDGE: "Approved KB knowledge changed since the lock was created",
    _SECTION_GOVERNANCE: "Engineering governance inputs changed since the lock was created",
}


def evaluate_lock(
    lock: ContextAssemblyLock, current: GovernedContextAssembly,
) -> LockStatusResponse:
    """Report whether ``lock`` is stale for ``current``, and why."""
    reasons: list[StalenessReason] = []
    for section, reason in _STALENESS_REASONS.items():
        locked_digest = lock.input_digests.get(section)
        current_digest = current.input_digests.get(section)
        if locked_digest != current_digest:
            reasons.append(
                StalenessReason(
                    section=section,
                    reason=reason,
                    locked_digest=locked_digest,
                    current_digest=current_digest,
                )
            )

    stale = bool(reasons) or lock.context_hash != current.context_hash
    if stale and not reasons:
        reasons.append(
            StalenessReason(
                section="assembly",
                reason="Context hash no longer matches the locked governed inputs",
                locked_digest=lock.context_hash,
                current_digest=current.context_hash,
            )
        )
    return LockStatusResponse(
        lock_id=lock.lock_id,
        stale=stale,
        locked_context_hash=lock.context_hash,
        current_context_hash=current.context_hash,
        reasons=reasons,
    )
