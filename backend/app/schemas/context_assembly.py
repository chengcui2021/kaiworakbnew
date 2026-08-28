"""Governed Context Assembly contract (Phase 1).

Structured request/response models for combining Requirement Analysis
Context, Repository Analysis Context, Knowledge Context and Engineering
Governance Context into one Governed Context Assembly, and for converting a
successful assembly into a Context Assembly Lock.

The contract is deliberately UI-agnostic: downstream consumers read the
structured fields below and never have to interpret frontend data shapes.
"""
from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


class EngineeringRequestInput(BaseModel):
    """The originating engineering request (Requirement Analysis input)."""

    model_config = ConfigDict(extra="forbid")
    id: str | None = Field(default=None, max_length=200)
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=1)
    acceptance_criteria: list[str] = Field(default_factory=list)
    source: str | None = Field(default=None, max_length=500)


class RepositoryFileInput(BaseModel):
    """A single file described by the caller. Never read from disk.

    ``context_role`` and ``access`` preserve execution semantics discovered by
    repository analysis. A file may be required for understanding/validation
    while remaining protected from mutation.
    """

    model_config = ConfigDict(extra="forbid")
    path: str = Field(..., min_length=1, max_length=1000)
    language: str | None = Field(default=None, max_length=100)
    role: str | None = Field(default=None, max_length=100)
    context_role: Literal["implementation", "verification"] = "implementation"
    access: Literal["read_write", "read_only"] = "read_write"


class RepositoryInput(BaseModel):
    """Repository information supplied to Repository Analysis.

    Analysis is metadata-only: the KB is given repository information and
    never clones, writes to, or otherwise modifies the target repository.
    """

    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1, max_length=300)
    url: str | None = Field(default=None, max_length=1000)
    branch: str | None = Field(default=None, max_length=300)
    commit_sha: str = Field(..., min_length=7, max_length=64)
    files: list[RepositoryFileInput] = Field(default_factory=list)


class KnowledgeSelectionInput(BaseModel):
    """Knowledge selection policy for a governed assembly.

    ``explicit`` preserves the existing caller-supplied entry-id path.
    ``automatic`` delegates selection to the KB resolver before assembly.
    """

    model_config = ConfigDict(extra="forbid")
    mode: Literal["explicit", "automatic"] = "explicit"
    entry_ids: list[str] = Field(default_factory=list)
    workstream_id: UUID | None = Field(
        default=None,
        description="Project/workstream knowledge scope used by automatic resolution.",
    )
    include_shared: bool = Field(
        default=True,
        description="Also consider approved entries without a workstream as shared knowledge.",
    )
    max_entries: int = Field(default=12, ge=1, le=50)
    min_similarity: float = Field(default=0.25, ge=-1.0, le=1.0)


class GovernanceRuleInput(BaseModel):
    """An engineering standard, policy, rule or guidance statement."""

    model_config = ConfigDict(extra="forbid")
    id: str = Field(..., min_length=1, max_length=200)
    title: str = Field(..., min_length=1, max_length=500)
    topic: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Governed subject. Two approved rules on the same topic "
        "that state different things are a governance conflict.",
    )
    rule: str = Field(..., min_length=1)
    source: str | None = Field(default=None, max_length=500)
    status: str = Field(default="approved", max_length=50)
    precedence: int = Field(
        default=0,
        description="Higher wins when two rules on the same topic disagree. "
        "Equal precedence cannot be resolved deterministically.",
    )




class RequirementAnalysisInput(BaseModel):
    """Requirement analysis produced by an external intelligence layer such as LingYu.

    KB does not reinterpret these fields; it validates, canonicalises and freezes
    them as part of the governed contract.
    """

    model_config = ConfigDict(extra="forbid")
    request_id: str | None = Field(default=None, max_length=200)
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=1)
    acceptance_criteria: list[str] = Field(default_factory=list)
    clarified_requirement: str | None = None
    constraints: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    source: str | None = Field(default=None, max_length=500)


class RepositoryAnalysisInput(BaseModel):
    """Repository understanding supplied by LingYu at an immutable repository SHA."""

    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1, max_length=300)
    url: str | None = Field(default=None, max_length=1000)
    branch: str | None = Field(default=None, max_length=300)
    commit_sha: str = Field(..., min_length=7, max_length=64)
    relevant_files: list[RepositoryFileInput] = Field(default_factory=list)
    impacted_components: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    architecture_context: list[str] = Field(default_factory=list)
    analysis_evidence: list[str] = Field(default_factory=list)


class KnowledgeResolutionRequest(BaseModel):
    """Standalone explainable knowledge-resolution request."""

    model_config = ConfigDict(extra="forbid")
    requirement_analysis: RequirementAnalysisInput
    repository_analysis: RepositoryAnalysisInput
    workstream_id: UUID | None = None
    tenant_id: str = Field(..., min_length=1, max_length=255)
    workspace_id: str = Field(..., min_length=1, max_length=255)
    repository_id: str = Field(..., min_length=1, max_length=2000)
    include_shared: bool = True
    max_entries: int = Field(default=12, ge=1, le=50)
    min_similarity: float = Field(default=0.25, ge=-1.0, le=1.0)


class GovernedContextFromAnalysisRequest(BaseModel):
    """Analysis-aware governed context input used by LingYu -> KB handoff."""

    model_config = ConfigDict(extra="forbid")
    analysis_source: str = Field(default="lingyu", min_length=1, max_length=100)
    analysis_id: str | None = Field(default=None, max_length=200)
    analysis_hash: str | None = Field(default=None, max_length=200)
    tenant_id: str = Field(default="default", min_length=1, max_length=255)
    workspace_id: str = Field(default="default", min_length=1, max_length=255)
    repository_id: str = Field(default="", max_length=2000)
    requirement_analysis: RequirementAnalysisInput
    repository_analysis: RepositoryAnalysisInput
    knowledge: KnowledgeSelectionInput = Field(default_factory=KnowledgeSelectionInput)
    governance: list[GovernanceRuleInput] = Field(default_factory=list)


class GovernedContextRequest(BaseModel):
    """Full input set for a Governed Context Assembly."""

    model_config = ConfigDict(extra="forbid")
    request: EngineeringRequestInput
    repository: RepositoryInput
    knowledge: KnowledgeSelectionInput = Field(default_factory=KnowledgeSelectionInput)
    governance: list[GovernanceRuleInput] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Context sections
# ---------------------------------------------------------------------------


class RequirementAnalysisContext(BaseModel):
    """Structured requirement authority frozen into the governed context."""

    request_id: str | None = None
    title: str
    description: str
    acceptance_criteria: list[str] = Field(default_factory=list)
    clarified_requirement: str | None = None
    constraints: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    analysis_source: str = "kb_structured_input"
    analysis_id: str | None = None
    analysis_hash: str | None = None
    tenant_id: str = "default"
    workspace_id: str = "default"
    repository_id: str = ""
    source: str | None = None
    digest: str


class RepositoryFileContext(BaseModel):
    path: str
    language: str | None = None
    role: str | None = None
    context_role: Literal["implementation", "verification"] = "implementation"
    access: Literal["read_write", "read_only"] = "read_write"


class RepositoryAnalysisContext(BaseModel):
    """Structured repository authority frozen at a specific commit SHA."""

    name: str
    url: str | None = None
    branch: str | None = None
    commit_sha: str
    file_count: int = 0
    languages: list[str] = Field(default_factory=list)
    top_level_paths: list[str] = Field(default_factory=list)
    files: list[RepositoryFileContext] = Field(default_factory=list)
    relevant_files: list[str] = Field(default_factory=list)
    impacted_components: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    architecture_context: list[str] = Field(default_factory=list)
    analysis_evidence: list[str] = Field(default_factory=list)
    analysis_source: str = "kb_structured_input"
    analysis_id: str | None = None
    analysis_hash: str | None = None
    analysis_mode: str = Field(
        default="read_only_metadata",
        description="Repository analysis never modifies the target repository.",
    )
    read_only: bool = True
    digest: str


class KnowledgeProvenance(BaseModel):
    """Source lineage for one KB-derived item."""

    entry_id: str
    title: str
    source: str | None = None
    version: str | None = Field(
        default=None, description="Updated timestamp used as the entry version."
    )
    updated_at: str | None = None
    status: str


class KnowledgeSnapshot(BaseModel):
    """Immutable content snapshot for one approved KB entry.

    Governed execution consumes this snapshot directly so it never has to
    re-fetch mutable KB knowledge after a Context Assembly Lock is created.
    """

    entry_id: str
    title: str
    content: str
    source: str | None = None
    version: str | None = None
    updated_at: str | None = None
    status: str


class ResolvedKnowledgeItem(BaseModel):
    """One approved entry selected by the governed knowledge resolver."""

    entry_id: str
    title: str
    source: str | None = None
    workstream_id: str | None = None
    scope: Literal["global", "tenant", "workspace", "repository", "workstream", "shared"]
    semantic_similarity: float | None = None
    lexical_score: float = 0.0
    score: float
    reason: str


class KnowledgeResolution(BaseModel):
    """Deterministic, explainable result of automatic knowledge selection."""

    resolver_version: str = "1"
    mode: Literal["automatic", "explicit_override"] = "automatic"
    query: str
    workstream_id: str | None = None
    include_shared: bool = True
    tenant_id: str = ""
    workspace_id: str = ""
    repository_id: str = ""
    selected: list[ResolvedKnowledgeItem] = Field(default_factory=list)
    resolution_hash: str


class KnowledgeContext(BaseModel):
    """Approved persistent knowledge selected for the assembly."""

    source_capability: str = Field(
        default="knowledge_context_assembly",
        description="Reuses the existing Knowledge Context Assembly selection "
        "and hashing used by Context Packages.",
    )
    approved_status: str
    entry_ids: list[str] = Field(default_factory=list)
    entry_count: int = 0
    provenance: list[KnowledgeProvenance] = Field(default_factory=list)
    snapshots: list[KnowledgeSnapshot] = Field(
        default_factory=list,
        description="Immutable authoritative/approved knowledge bodies frozen into the governed context.",
    )
    learning_snapshots: list[KnowledgeSnapshot] = Field(
        default_factory=list,
        description="Immutable validated learned knowledge. Candidate learning is never included.",
    )
    resolution: KnowledgeResolution | None = Field(
        default=None,
        description="Explainable automatic/override selection evidence frozen with the context.",
    )
    knowledge_hash: str
    digest: str


class GovernanceRuleContext(BaseModel):
    id: str
    title: str
    topic: str
    rule: str
    source: str | None = None
    precedence: int = 0


class GovernanceConflict(BaseModel):
    """Two or more approved rules on one topic that disagree at equal precedence."""

    topic: str
    rule_ids: list[str] = Field(default_factory=list)
    reason: str


class GovernanceSupersession(BaseModel):
    """A rule deterministically overridden by a higher-precedence rule."""

    topic: str
    superseded_rule_id: str
    superseded_by_rule_id: str


class EngineeringGovernanceContext(BaseModel):
    """Applicable approved engineering governance for this assembly."""

    rules: list[GovernanceRuleContext] = Field(default_factory=list)
    excluded_rule_ids: list[str] = Field(
        default_factory=list, description="Ineligible (not approved) rules, dropped."
    )
    superseded: list[GovernanceSupersession] = Field(default_factory=list)
    digest: str


# ---------------------------------------------------------------------------
# Assembly + lock
# ---------------------------------------------------------------------------


class GovernedContextAssembly(BaseModel):
    """The four governed context sections combined into one structure."""

    assembly_version: str
    requirement_context: RequirementAnalysisContext
    repository_context: RepositoryAnalysisContext
    knowledge_context: KnowledgeContext
    governance_context: EngineeringGovernanceContext
    input_digests: dict[str, str] = Field(
        default_factory=dict,
        description="Per-section digests the context hash is derived from.",
    )
    context_hash: str = Field(
        ..., description="Canonical hash. Identical governed inputs hash identically."
    )
    created_at: str = Field(..., description="Not part of the context hash.")


class GovernedInputsRef(BaseModel):
    """Identifies the governed inputs a lock was produced from."""

    request_id: str | None = None
    request_digest: str
    repository_commit_sha: str
    repository_digest: str
    knowledge_entry_ids: list[str] = Field(default_factory=list)
    knowledge_hash: str
    governance_rule_ids: list[str] = Field(default_factory=list)
    governance_digest: str


class ContextAssemblyLock(BaseModel):
    """A Governed Context Assembly frozen for downstream consumption.

    ``governed_context`` is carried as the immutable snapshot for consumers
    that receive the lock directly. It is optional for backward compatibility
    with already-persisted pre-V5 lock payloads.
    """

    lock_id: str
    assembly_version: str
    context_hash: str
    input_digests: dict[str, str] = Field(default_factory=dict)
    governed_inputs: GovernedInputsRef
    created_at: str
    governed_context: GovernedContextAssembly | None = None

    def model_dump(self, *args, **kwargs):
        """Preserve the legacy wire contract when no snapshot is attached.

        ``governed_context`` is an opt-in extension used by analysis-derived
        locks.  Omitting only this top-level optional extension keeps nested
        nullable contract fields such as ``governed_inputs.request_id`` intact.
        """
        payload = super().model_dump(*args, **kwargs)
        if self.governed_context is None:
            payload.pop("governed_context", None)
        return payload


class ContextAssemblyLockResource(BaseModel):
    """Persisted downstream contract: lock plus the exact governed assembly snapshot it froze."""

    lock: ContextAssemblyLock
    governed_context: GovernedContextAssembly


class LockStalenessRequest(BaseModel):
    """Compare an existing lock against the current governed inputs."""

    model_config = ConfigDict(extra="forbid")
    lock: ContextAssemblyLock
    current: GovernedContextRequest


class StalenessReason(BaseModel):
    section: str
    reason: str
    locked_digest: str | None = None
    current_digest: str | None = None


class LockStatusResponse(BaseModel):
    lock_id: str
    stale: bool
    locked_context_hash: str
    current_context_hash: str
    reasons: list[StalenessReason] = Field(default_factory=list)


class GovernanceConflictResponse(BaseModel):
    """400/409 body when governance cannot be resolved deterministically."""

    error: str = "governance_conflict"
    message: str
    conflicts: list[GovernanceConflict] = Field(default_factory=list)
