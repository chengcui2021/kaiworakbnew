"""Context Package routes -- approved knowledge bundled with an integrity hash.

All access is scoped to a single workspace. A package can only be created from
KB entries that are (a) in this workspace and (b) approved.
"""
from __future__ import annotations

import itertools
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.database import get_db
from app.schemas.models import ContextPackage, ContextPackageCreate
from app.services.knowledge_context import (
    UnapprovedEntryError,
    UnknownEntryIdsError,
    compute_entry_context_hash,
    select_approved_entries,
)
from app.services.store import ApprovalConstraintError, store

router = APIRouter(prefix="/api/workspaces/{workspace_id}/packages", tags=["packages"])

# Packages created from persistent KB entries are kept in memory alongside the
# workspace-store packages for this prototype runtime. This preserves the new
# PostgreSQL-backed KB console while keeping the existing ContextPackage API.
_persistent_packages: dict[str, ContextPackage] = {}
_persistent_pkg_counter = itertools.count(1)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_workspace(workspace_id: str) -> None:
    if store.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail=f"Workspace '{workspace_id}' not found")


@router.get("", response_model=list[ContextPackage])
def list_context_packages(workspace_id: str) -> list[ContextPackage]:
    _require_workspace(workspace_id)
    packages = store.list_context_packages(workspace_id)
    persistent = [p for p in _persistent_packages.values() if p.workspace_id == workspace_id]
    persistent.sort(key=lambda p: p.created_at, reverse=True)
    return [*persistent, *packages]


@router.post("", response_model=ContextPackage, status_code=201)
async def create_context_package(
    workspace_id: str,
    payload: ContextPackageCreate,
    db: AsyncSession = Depends(get_db),
) -> ContextPackage:
    _require_workspace(workspace_id)
    package_name = payload.name.strip()

    # First preserve the original workspace-document behaviour. This supports
    # seeded workspace documents and the Workspace Detail approval flow.
    try:
        return store.create_context_package(workspace_id, package_name, payload.selected_entry_ids)
    except ApprovalConstraintError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Only approved entries can be packaged. Not approved: {exc.entry_ids}",
        ) from exc
    except KeyError:
        # Fall through to the persistent KB path below. The restored Submit /
        # Browse / Search console stores entries in PostgreSQL, not in the
        # workspace mock store, so UUID entry ids will not exist as documents.
        pass

    # Shared Knowledge Context Assembly selection: resolves the ids and
    # enforces the approved (resolved) knowledge constraint.
    try:
        entries = await select_approved_entries(db, payload.selected_entry_ids)
    except UnknownEntryIdsError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"One or more entries were not found in this workspace: {exc.entry_ids}",
        ) from exc
    except UnapprovedEntryError as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                "Only approved/resolved entries can be packaged. "
                f"Not approved/resolved: {exc.entry_ids}"
            ),
        ) from exc

    package = ContextPackage(
        id=f"pkg-persistent-{next(_persistent_pkg_counter)}",
        name=package_name,
        workspace_id=workspace_id,
        selected_entry_ids=[str(e.id) for e in entries],
        created_at=_now(),
        approval_status="approved",
        context_hash=compute_entry_context_hash(entries),
        entry_titles=[e.title for e in entries],
    )
    _persistent_packages[package.id] = package
    return package
