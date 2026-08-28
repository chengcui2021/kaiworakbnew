"""Governed Context Assembly routes (Phase 1).

Structured backend contract for combining Requirement Analysis Context,
Repository Analysis Context, Knowledge Context and Engineering Governance
Context into one Governed Context Assembly, converting it into a Context
Assembly Lock, and checking an existing lock for staleness.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.database import get_db
from app.persistence.embeddings import EmbeddingService, get_embedding_service
from app.persistence.models import ContextAssemblyLockDB
from app.schemas.context_assembly import (
    ContextAssemblyLock,
    ContextAssemblyLockResource,
    GovernedContextAssembly,
    GovernedContextFromAnalysisRequest,
    GovernedContextRequest,
    LockStalenessRequest,
    KnowledgeResolution,
    KnowledgeResolutionRequest,
    LockStatusResponse,
)
from app.services.context_assembly import (
    GovernanceConflictError,
    RepositoryValidationError,
    RequirementValidationError,
    assemble_governed_context,
    build_governance_context,
    build_knowledge_context,
    build_repository_context,
    build_repository_context_from_analysis,
    build_requirement_context,
    build_requirement_context_from_analysis,
    evaluate_lock,
    lock_assembly,
)
from app.services.learning_service import reusable as reusable_learning
from app.services.knowledge_resolver import (
    KnowledgeResolutionError,
    KnowledgeResolutionUnavailableError,
    resolve_knowledge,
)
from app.services.tenant_scope import filter_authorized_entries
from app.services.knowledge_context import (
    UnapprovedEntryError,
    UnknownEntryIdsError,
    select_approved_entries,
)

router = APIRouter(prefix="/api/governed-context", tags=["governed-context"])


async def _assemble(payload: GovernedContextRequest, db: AsyncSession) -> GovernedContextAssembly:
    """Build every governed section, mapping domain errors to HTTP responses."""
    try:
        requirement = build_requirement_context(payload.request)
    except RequirementValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    try:
        repository = build_repository_context(payload.repository)
    except RepositoryValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    # Reuses the Knowledge Context Assembly selection shared with Context
    # Packages, so only approved (resolved) knowledge can enter the context.
    try:
        entries = await select_approved_entries(db, payload.knowledge.entry_ids)
    except UnknownEntryIdsError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"One or more entries were not found: {exc.entry_ids}",
        ) from exc
    except UnapprovedEntryError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Only approved/resolved knowledge can enter a governed context. "
                f"Not approved/resolved: {exc.entry_ids}"
            ),
        ) from exc
    entries = filter_authorized_entries(entries, tenant_id="", workspace_id="", repository_id="")
    if len(entries) != len(payload.knowledge.entry_ids):
        raise HTTPException(status_code=404, detail="One or more knowledge entries are outside the authorised scope")
    knowledge = build_knowledge_context(entries)

    try:
        governance = build_governance_context(payload.governance)
    except GovernanceConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "governance_conflict",
                "message": str(exc),
                "conflicts": [c.model_dump() for c in exc.conflicts],
            },
        ) from exc

    return assemble_governed_context(requirement, repository, knowledge, governance)


async def _assemble_from_analysis(
    payload: GovernedContextFromAnalysisRequest, db: AsyncSession
) -> GovernedContextAssembly:
    """Govern LingYu analysis without asking KB to re-run requirement/repository intelligence."""
    try:
        requirement = build_requirement_context_from_analysis(
            payload.requirement_analysis,
            analysis_source=payload.analysis_source,
            analysis_id=payload.analysis_id,
            analysis_hash=payload.analysis_hash,
            tenant_id=payload.tenant_id,
            workspace_id=payload.workspace_id,
            repository_id=payload.repository_id or str(payload.repository_analysis.url or payload.repository_analysis.name or ""),
        )
    except RequirementValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    try:
        repository = build_repository_context_from_analysis(
            payload.repository_analysis,
            analysis_source=payload.analysis_source,
            analysis_id=payload.analysis_id,
            analysis_hash=payload.analysis_hash,
        )
    except RepositoryValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    resolution: KnowledgeResolution | None = None
    entry_ids = list(payload.knowledge.entry_ids)
    if payload.knowledge.mode == "automatic":
        try:
            # Resolve lazily so the long-standing explicit-id path does not
            # require Bedrock/embedding availability or change behaviour.
            resolution = await resolve_knowledge(
                db,
                get_embedding_service(),
                requirement=payload.requirement_analysis,
                repository=payload.repository_analysis,
                workstream_id=payload.knowledge.workstream_id,
                tenant_id=payload.tenant_id,
                workspace_id=payload.workspace_id,
                repository_id=payload.repository_id or str(payload.repository_analysis.url or payload.repository_analysis.name or ""),
                include_shared=payload.knowledge.include_shared,
                max_entries=payload.knowledge.max_entries,
                min_similarity=payload.knowledge.min_similarity,
            )
            entry_ids = [item.entry_id for item in resolution.selected]
        except KnowledgeResolutionUnavailableError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
            ) from exc
        except KnowledgeResolutionError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
            ) from exc
    try:
        # Existing approval gate remains authoritative even for resolver output.
        entries = await select_approved_entries(db, entry_ids)
    except UnknownEntryIdsError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"One or more entries were not found: {exc.entry_ids}") from exc
    except UnapprovedEntryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=(
            "Only approved/resolved knowledge can enter a governed context. "
            f"Not approved/resolved: {exc.entry_ids}"
        )) from exc
    authorised_entries = filter_authorized_entries(
        entries, tenant_id=payload.tenant_id, workspace_id=payload.workspace_id,
        repository_id=payload.repository_id or str(payload.repository_analysis.url or payload.repository_analysis.name or ""),
    )
    if len(authorised_entries) != len(entries):
        raise HTTPException(status_code=404, detail="One or more knowledge entries are outside the authorised tenant scope")
    entries = authorised_entries
    learning_entries = await reusable_learning(
        db,
        payload.tenant_id,
        payload.workspace_id,
        payload.repository_id or str(payload.repository_analysis.url or payload.repository_analysis.name or ""),
    )
    knowledge = build_knowledge_context(entries, resolution=resolution, learning_entries=learning_entries)
    try:
        governance = build_governance_context(payload.governance)
    except GovernanceConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={
            "error": "governance_conflict", "message": str(exc),
            "conflicts": [c.model_dump() for c in exc.conflicts],
        }) from exc
    return assemble_governed_context(requirement, repository, knowledge, governance)


@router.post(
    "/resolve-knowledge",
    response_model=KnowledgeResolution,
    summary="Resolve approved KB knowledge for LingYu requirement and repository analysis",
)
async def resolve_context_knowledge(
    payload: KnowledgeResolutionRequest,
    db: AsyncSession = Depends(get_db),
    embedder: EmbeddingService = Depends(get_embedding_service),
) -> KnowledgeResolution:
    try:
        return await resolve_knowledge(
            db,
            embedder,
            requirement=payload.requirement_analysis,
            repository=payload.repository_analysis,
            workstream_id=payload.workstream_id,
            tenant_id=payload.tenant_id,
            workspace_id=payload.workspace_id,
            repository_id=payload.repository_id,
            include_shared=payload.include_shared,
            max_entries=payload.max_entries,
            min_similarity=payload.min_similarity,
        )
    except KnowledgeResolutionUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except KnowledgeResolutionError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post(
    "/assemble-from-analysis",
    response_model=GovernedContextAssembly,
    summary="Assemble governed context from LingYu requirement and repository analysis",
)
async def assemble_context_from_analysis(
    payload: GovernedContextFromAnalysisRequest,
    db: AsyncSession = Depends(get_db),
) -> GovernedContextAssembly:
    return await _assemble_from_analysis(payload, db)


@router.post(
    "/lock-from-analysis",
    response_model=ContextAssemblyLock,
    status_code=status.HTTP_201_CREATED,
    summary="Create a reusable Context Assembly Lock from LingYu analysis",
)
async def create_context_lock_from_analysis(
    payload: GovernedContextFromAnalysisRequest,
    db: AsyncSession = Depends(get_db),
) -> ContextAssemblyLock:
    assembly = await _assemble_from_analysis(payload, db)
    lock = lock_assembly(assembly)
    row = await db.get(ContextAssemblyLockDB, lock.lock_id)
    lock_payload = lock.model_dump(mode="json")
    assembly_payload = assembly.model_dump(mode="json")
    request_payload = {
        "source_type": "external_analysis",
        "payload": payload.model_dump(mode="json"),
    }
    if row is None:
        row = ContextAssemblyLockDB(
            lock_id=lock.lock_id, context_hash=lock.context_hash,
            lock_payload=lock_payload, assembly_payload=assembly_payload,
            request_payload=request_payload,
            tenant_id=payload.tenant_id,
            workspace_id=payload.workspace_id,
            repository_id=payload.repository_id or str(payload.repository_analysis.url or payload.repository_analysis.name or ""),
        )
        db.add(row)
    else:
        row.context_hash = lock.context_hash
        row.lock_payload = lock_payload
        row.assembly_payload = assembly_payload
        row.request_payload = request_payload
        row.tenant_id = payload.tenant_id
        row.workspace_id = payload.workspace_id
        row.repository_id = payload.repository_id or str(payload.repository_analysis.url or payload.repository_analysis.name or "")
    await db.commit()
    return lock


@router.post(
    "/assemble",
    response_model=GovernedContextAssembly,
    summary="Assemble a Governed Context from requirement, repository, knowledge and governance inputs",
)
async def assemble_context(
    payload: GovernedContextRequest,
    db: AsyncSession = Depends(get_db),
) -> GovernedContextAssembly:
    return await _assemble(payload, db)


@router.post(
    "/lock",
    response_model=ContextAssemblyLock,
    status_code=status.HTTP_201_CREATED,
    summary="Convert a successful Governed Context Assembly into a Context Assembly Lock",
)
async def create_context_lock(
    payload: GovernedContextRequest,
    db: AsyncSession = Depends(get_db),
) -> ContextAssemblyLock:
    assembly = await _assemble(payload, db)
    lock = lock_assembly(assembly)
    row = await db.get(ContextAssemblyLockDB, lock.lock_id)
    lock_payload = lock.model_dump(mode="json")
    assembly_payload = assembly.model_dump(mode="json")
    request_payload = {"source_type": "raw_request", "payload": payload.model_dump(mode="json")}
    if row is None:
        row = ContextAssemblyLockDB(
            lock_id=lock.lock_id,
            context_hash=lock.context_hash,
            lock_payload=lock_payload,
            assembly_payload=assembly_payload,
            request_payload=request_payload,
        )
        db.add(row)
    else:
        row.context_hash = lock.context_hash
        row.lock_payload = lock_payload
        row.assembly_payload = assembly_payload
        row.request_payload = request_payload
    await db.commit()
    return lock




def _lock_scope_matches(
    row: ContextAssemblyLockDB,
    *,
    tenant_id: str | None,
    workspace_id: str | None,
    repository_id: str | None,
) -> bool:
    """Authorise persisted lock access without weakening Cloud isolation.

    Cloud locks (non-default tenant/workspace) always require the complete
    server-derived scope tuple. Legacy/internal locks created before Cloud
    tenancy used the reserved ``default/default`` scope and remain retrievable
    without query parameters for backwards compatibility.
    """
    supplied = (tenant_id, workspace_id, repository_id)
    if all(value is None for value in supplied):
        return str(row.tenant_id or "default") == "default" and str(row.workspace_id or "default") == "default"
    if any(value is None for value in supplied):
        return False
    return (
        str(row.tenant_id) == str(tenant_id)
        and str(row.workspace_id) == str(workspace_id)
        and str(row.repository_id or "") == str(repository_id or "")
    )


@router.get(
    "/locks/{lock_id}",
    response_model=ContextAssemblyLockResource,
    summary="Retrieve a persisted Context Assembly Lock and its governed assembly snapshot by ID",
)
async def get_context_lock(
    lock_id: str,
    tenant_id: str | None = Query(default=None, min_length=1),
    workspace_id: str | None = Query(default=None, min_length=1),
    repository_id: str | None = Query(default=None, min_length=1),
    db: AsyncSession = Depends(get_db),
) -> ContextAssemblyLockResource:
    row = await db.get(ContextAssemblyLockDB, lock_id)
    if row is None or not _lock_scope_matches(
        row, tenant_id=tenant_id, workspace_id=workspace_id, repository_id=repository_id
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Context Assembly Lock not found")
    return ContextAssemblyLockResource(
        lock=ContextAssemblyLock.model_validate(row.lock_payload),
        governed_context=GovernedContextAssembly.model_validate(row.assembly_payload),
    )


@router.get(
    "/locks/{lock_id}/status",
    response_model=LockStatusResponse,
    summary="Check a persisted Context Assembly Lock against current governed inputs",
)
async def get_context_lock_status(
    lock_id: str,
    tenant_id: str | None = Query(default=None, min_length=1),
    workspace_id: str | None = Query(default=None, min_length=1),
    repository_id: str | None = Query(default=None, min_length=1),
    db: AsyncSession = Depends(get_db),
) -> LockStatusResponse:
    row = await db.get(ContextAssemblyLockDB, lock_id)
    if row is None or not _lock_scope_matches(
        row, tenant_id=tenant_id, workspace_id=workspace_id, repository_id=repository_id
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Context Assembly Lock not found")
    lock = ContextAssemblyLock.model_validate(row.lock_payload)
    stored = row.request_payload or {}
    source_type = stored.get("source_type") if isinstance(stored, dict) else None
    source_payload = stored.get("payload") if source_type and isinstance(stored, dict) else stored
    if source_type == "external_analysis":
        current_request = GovernedContextFromAnalysisRequest.model_validate(source_payload)
        current = await _assemble_from_analysis(current_request, db)
    else:
        current_request = GovernedContextRequest.model_validate(source_payload)
        current = await _assemble(current_request, db)
    return evaluate_lock(lock, current)


@router.post(
    "/lock/status",
    response_model=LockStatusResponse,
    summary="Check an existing Context Assembly Lock against the current governed inputs",
)
async def check_context_lock(
    payload: LockStalenessRequest,
    db: AsyncSession = Depends(get_db),
) -> LockStatusResponse:
    current = await _assemble(payload.current, db)
    return evaluate_lock(payload.lock, current)
