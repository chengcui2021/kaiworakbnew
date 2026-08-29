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
    fp = fingerprint(payload["tenant_id"], repository_id, payload.get("knowledge_type", "procedural"), payload["observation"], scope)
    evidence = dict(payload.get("evidence") or {})
    confidence = max(0, min(100, round(float(payload.get("confidence", 0)) * 100)))
    q = select(func.count(LearningEntryDB.id)).where(LearningEntryDB.tenant_id == payload["tenant_id"], LearningEntryDB.fingerprint == fp)
    prior = int((await db.execute(q)).scalar() or 0)
    evidence["occurrence_count"] = prior + 1
    evidence["successful_run_count"] = int(bool(evidence.get("run_success")))
    evidence["failure_run_count"] = int(not bool(evidence.get("run_success")))
    evidence["reusability_score"] = min(100, confidence + min(prior * 5, 15))
    evidence["privacy_scope"] = scope
    row = LearningEntryDB(
        tenant_id=payload["tenant_id"], workspace_id=payload.get("workspace_id", "default"), repository_id=repository_id,
        knowledge_type=payload.get("knowledge_type", "procedural"), scope=scope, observation=payload["observation"], fingerprint=fp,
        status=CANDIDATE, confidence=confidence, source_run_id=payload.get("project_run_id", ""), source_commit=payload.get("source_commit", ""),
        evidence=evidence, provenance=payload.get("provenance") or {},
    )
    db.add(row); await db.commit(); await db.refresh(row); return row


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
