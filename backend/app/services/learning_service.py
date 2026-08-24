from __future__ import annotations
import hashlib, json, re
from datetime import datetime, UTC
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.persistence.models import LearningEntryDB

VALIDATED = "validated"
CANDIDATE = "candidate"

def fingerprint(tenant_id: str, repository_id: str, knowledge_type: str, observation: str) -> str:
    norm = re.sub(r"\s+", " ", observation.strip().lower())
    return hashlib.sha256(f"{tenant_id}|{repository_id}|{knowledge_type}|{norm}".encode()).hexdigest()

async def create_candidate(db: AsyncSession, payload: dict):
    fp=fingerprint(payload['tenant_id'], payload.get('repository_id',''), payload.get('knowledge_type','procedural'), payload['observation'])
    evidence=payload.get('evidence') or {}
    confidence=max(0,min(100,round(float(payload.get('confidence',0))*100)))
    successful=bool(evidence.get('run_success')) and bool((evidence.get('final_validation') or {}).get('ok', evidence.get('run_success')))
    q=select(func.count(LearningEntryDB.id)).where(LearningEntryDB.tenant_id==payload['tenant_id'], LearningEntryDB.repository_id==payload.get('repository_id',''), LearningEntryDB.fingerprint==fp, LearningEntryDB.status.in_([CANDIDATE,VALIDATED]))
    prior=int((await db.execute(q)).scalar() or 0)
    # Zero-admin, conservative auto-promotion: a single run is never enough.
    # Repeated successful evidence with high confidence promotes automatically.
    status=VALIDATED if successful and confidence>=80 and prior>=1 else CANDIDATE
    row=LearningEntryDB(tenant_id=payload['tenant_id'],workspace_id=payload.get('workspace_id','default'),repository_id=payload.get('repository_id',''),knowledge_type=payload.get('knowledge_type','procedural'),scope=payload.get('scope','repository'),observation=payload['observation'],fingerprint=fp,status=status,confidence=confidence,source_run_id=payload.get('project_run_id',''),source_commit=payload.get('source_commit',''),evidence=evidence,provenance=payload.get('provenance') or {})
    if status==VALIDATED: row.validated_at=datetime.now(UTC)
    db.add(row); await db.commit(); await db.refresh(row)
    return row

async def reusable(db: AsyncSession, tenant_id: str, workspace_id: str, repository_id: str):
    stmt=select(LearningEntryDB).where(LearningEntryDB.tenant_id==tenant_id, LearningEntryDB.workspace_id==workspace_id, LearningEntryDB.repository_id==repository_id, LearningEntryDB.status==VALIDATED).order_by(LearningEntryDB.confidence.desc(), LearningEntryDB.created_at.desc()).limit(20)
    return list((await db.execute(stmt)).scalars().all())
