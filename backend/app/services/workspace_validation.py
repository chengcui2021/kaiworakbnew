"""Workspace validation service.

Runs three on-demand checks against a workspace to prove that workspace
isolation guarantees hold:

1. ``search_scope``        -- a sample search returns only documents from the
                              selected workspace.
2. ``document_ownership``  -- every document reported for the workspace carries
                              the matching ``workspace_id``.
3. ``statistics``          -- the reported ``document_count`` matches an actual
                              count of stored documents.

Results are computed on demand and are not persisted.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.schemas.models import ValidationCheck, WorkspaceValidationResult
from app.services.store import WorkspaceStore


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _check_search_scope(store: WorkspaceStore, workspace_id: str) -> ValidationCheck:
    """Run sample searches and confirm no cross-workspace documents leak."""
    scoped = store.list_documents(workspace_id)
    # Build a sample of query terms from this workspace's own documents.
    sample_terms = []
    for doc in scoped[:3]:
        token = doc.title.split()[0] if doc.title.split() else ""
        if token:
            sample_terms.append(token)
    if not sample_terms:
        sample_terms = ["the"]

    leaked = []
    for term in sample_terms:
        for result in store.search_documents(workspace_id, term):
            if result.workspace_id != workspace_id:
                leaked.append(result.id)

    if leaked:
        return ValidationCheck(
            name="search_scope",
            label="Search scoped correctly",
            status="fail",
            message=f"{len(leaked)} document(s) from another workspace leaked into search results.",
            details={"leaked_document_ids": leaked, "sample_terms": sample_terms},
        )
    return ValidationCheck(
        name="search_scope",
        label="Search scoped correctly",
        status="pass",
        message=f"Sample searches ({len(sample_terms)} term(s)) returned only this workspace's documents.",
        details={"sample_terms": sample_terms},
    )


def _check_document_ownership(store: WorkspaceStore, workspace_id: str) -> ValidationCheck:
    """Confirm every document listed for the workspace belongs to it."""
    scoped = store.list_documents(workspace_id)
    mismatched = [d.id for d in scoped if d.workspace_id != workspace_id]
    if mismatched:
        return ValidationCheck(
            name="document_ownership",
            label="Documents belong to selected workspace",
            status="fail",
            message=f"{len(mismatched)} document(s) do not belong to this workspace.",
            details={"mismatched_document_ids": mismatched},
        )
    return ValidationCheck(
        name="document_ownership",
        label="Documents belong to selected workspace",
        status="pass",
        message=f"All {len(scoped)} document(s) belong to this workspace.",
        details={"document_count": len(scoped)},
    )


def _check_statistics(store: WorkspaceStore, workspace_id: str) -> ValidationCheck:
    """Confirm reported document_count matches the real stored count."""
    ws = store.get_workspace(workspace_id)
    actual = len(store.list_documents(workspace_id))
    reported = ws.document_count if ws else None
    if reported != actual:
        return ValidationCheck(
            name="statistics",
            label="Workspace statistics load successfully",
            status="fail",
            message=f"Reported count ({reported}) does not match actual count ({actual}).",
            details={"reported": reported, "actual": actual},
        )
    return ValidationCheck(
        name="statistics",
        label="Workspace statistics load successfully",
        status="pass",
        message=f"Statistics loaded: {actual} document(s) counted correctly.",
        details={"document_count": actual},
    )


def validate_workspace(store: WorkspaceStore, workspace_id: str) -> WorkspaceValidationResult:
    ws = store.get_workspace(workspace_id)
    if ws is None:
        raise KeyError(workspace_id)

    checks: list[ValidationCheck] = []
    for check_fn in (_check_search_scope, _check_document_ownership, _check_statistics):
        try:
            checks.append(check_fn(store, workspace_id))
        except Exception as exc:  # pragma: no cover - defensive
            checks.append(ValidationCheck(
                name=check_fn.__name__,
                label=check_fn.__name__,
                status="warning",
                message=f"Check could not complete: {exc}",
            ))

    if any(c.status == "fail" for c in checks):
        overall = "fail"
    elif any(c.status == "warning" for c in checks):
        overall = "warning"
    else:
        overall = "pass"

    return WorkspaceValidationResult(
        workspace_id=workspace_id,
        workspace_name=ws.name,
        validated_at=_now(),
        overall_status=overall,
        checks=checks,
    )
