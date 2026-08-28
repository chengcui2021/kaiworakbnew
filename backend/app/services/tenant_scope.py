"""Database-level tenant visibility predicates for Kaiwora Cloud knowledge."""
from __future__ import annotations

from sqlalchemy import and_, or_

VALID_SCOPES = {"global", "tenant", "workspace", "repository"}


def entry_scope_predicate(*, tenant_id: str, workspace_id: str, repository_id: str):
    """Return the authorised knowledge predicate.

    Filtering happens in SQL before vector ranking. Customer A rows are never
    candidates in Customer B's similarity search.
    """
    from app.persistence.models import Entry
    tenant_id = str(tenant_id or "").strip()
    workspace_id = str(workspace_id or "").strip()
    repository_id = str(repository_id or "").strip()
    clauses = [Entry.owner_scope == "global"]
    if tenant_id:
        clauses.append(and_(Entry.owner_scope == "tenant", Entry.tenant_id == tenant_id))
    if tenant_id and workspace_id:
        clauses.append(and_(
            Entry.owner_scope == "workspace",
            Entry.tenant_id == tenant_id,
            Entry.workspace_id == workspace_id,
        ))
    if tenant_id and workspace_id and repository_id:
        clauses.append(and_(
            Entry.owner_scope == "repository",
            Entry.tenant_id == tenant_id,
            Entry.workspace_id == workspace_id,
            Entry.repository_id == repository_id,
        ))
    return or_(*clauses)


def validate_entry_ownership(scope: str, tenant_id: str | None, workspace_id: str | None, repository_id: str | None) -> None:
    if scope not in VALID_SCOPES:
        raise ValueError(f"Unknown knowledge scope: {scope}")
    if scope == "global":
        return
    if not tenant_id:
        raise ValueError(f"{scope} knowledge requires tenant_id")
    if scope in {"workspace", "repository"} and not workspace_id:
        raise ValueError(f"{scope} knowledge requires workspace_id")
    if scope == "repository" and not repository_id:
        raise ValueError("repository knowledge requires repository_id")


def entry_is_authorized(entry, *, tenant_id: str, workspace_id: str, repository_id: str) -> bool:
    scope = str(getattr(entry, "owner_scope", "global") or "global")
    if scope == "global":
        return True
    if str(getattr(entry, "tenant_id", "") or "") != str(tenant_id or ""):
        return False
    if scope == "tenant":
        return True
    if str(getattr(entry, "workspace_id", "") or "") != str(workspace_id or ""):
        return False
    if scope == "workspace":
        return True
    if scope == "repository":
        return str(getattr(entry, "repository_id", "") or "") == str(repository_id or "")
    return False


def filter_authorized_entries(entries, *, tenant_id: str, workspace_id: str, repository_id: str):
    return [e for e in entries if entry_is_authorized(e, tenant_id=tenant_id, workspace_id=workspace_id, repository_id=repository_id)]
