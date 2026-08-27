from __future__ import annotations
import hashlib, re
from datetime import datetime, UTC
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.persistence.models import LearningEntryDB

VALIDATED = "validated"
CANDIDATE = "candidate"
_ALLOWED_SCOPES = {"repository", "workspace", "tenant", "shared"}


def _scope(payload: dict) -> str:
    value = str(payload.get("scope") or "repository").strip().lower()
    return value if value in _ALLOWED_SCOPES else "repository"


def fingerprint(tenant_id: str, repository_id: str, knowledge_type: str, observation: str, scope: str = "repository") -> str:
    norm = re.sub(r"\s+", " ", observation.strip().lower())
    repo_key = repository_id if scope == "repository" else "*"
    return hashlib.sha256(f"{tenant_id}|{scope}|{repo_key}|{knowledge_type}|{norm}".encode()).hexdigest()


async def create_candidate(db: AsyncSession, payload: dict):
    scope = _scope(payload)
    repository_id = str(payload.get("repository_id", "") or "")
    fp = fingerprint(
        payload["tenant_id"], repository_id,
        payload.get("knowledge_type", "procedural"), payload["observation"], scope,
    )
    evidence = payload.get("evidence") or {}
    confidence = max(0, min(100, round(float(payload.get("confidence", 0)) * 100)))
    successful = bool(evidence.get("run_success")) and bool(
        (evidence.get("final_validation") or {}).get("ok", evidence.get("run_success"))
    )
    q = select(func.count(LearningEntryDB.id)).where(
        LearningEntryDB.tenant_id == payload["tenant_id"],
        LearningEntryDB.fingerprint == fp,
        LearningEntryDB.status.in_([CANDIDATE, VALIDATED]),
    )
    prior = int((await db.execute(q)).scalar() or 0)
    # Conservative auto-promotion: one successful run is never enough.
    # Repeated successful evidence with high confidence may become reusable.
    status = VALIDATED if successful and confidence >= 80 and prior >= 1 else CANDIDATE
    row = LearningEntryDB(
        tenant_id=payload["tenant_id"],
        workspace_id=payload.get("workspace_id", "default"),
        repository_id=repository_id,
        knowledge_type=payload.get("knowledge_type", "procedural"),
        scope=scope,
        observation=payload["observation"], fingerprint=fp, status=status,
        confidence=confidence, source_run_id=payload.get("project_run_id", ""),
        source_commit=payload.get("source_commit", ""), evidence=evidence,
        provenance=payload.get("provenance") or {},
    )
    if status == VALIDATED:
        row.validated_at = datetime.now(UTC)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def reusable(db: AsyncSession, tenant_id: str, workspace_id: str, repository_id: str):
    """Return reusable learned intelligence for the next Context Lock.

    Repository-scoped learning stays private to that repo. Workspace/tenant
    learning can guide future repositories for the same customer, while shared
    learning is reserved for deliberately promoted Kaiwora baseline knowledge.
    """
    stmt = select(LearningEntryDB).where(
        LearningEntryDB.tenant_id == tenant_id,
        LearningEntryDB.status == VALIDATED,
        or_(
            (LearningEntryDB.scope == "repository") & (LearningEntryDB.repository_id == repository_id),
            (LearningEntryDB.scope == "workspace") & (LearningEntryDB.workspace_id == workspace_id),
            LearningEntryDB.scope.in_(["tenant", "shared"]),
        ),
    ).order_by(LearningEntryDB.confidence.desc(), LearningEntryDB.created_at.desc()).limit(30)
    return list((await db.execute(stmt)).scalars().all())
