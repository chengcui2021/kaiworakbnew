from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.persistence.database import get_db
from app.persistence.embeddings import EmbeddingService, get_embedding_service
from app.persistence.models import Entry, EntryStatus, EntryType, ComponentName, LearningEntryDB
from app.services.learning_service import create_candidate, reusable
from app.services.global_learning_service import maybe_create_global_candidate

router=APIRouter(prefix="/api/internal/learning", tags=["governed-learning"])

class CandidateLearningCreate(BaseModel):
    model_config=ConfigDict(extra="forbid")
    tenant_id: str = "default"
    workspace_id: str = "default"
    repository_id: str = ""
    project_run_id: str
    source_commit: str = ""
    knowledge_type: str = "procedural"
    scope: str = "repository"
    observation: str = Field(min_length=1)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: dict[str,Any] = {}
    provenance: dict[str,Any] = {}
    global_learning_contribution: bool = False
    workstream_id: str | None = None

def view(row):
    evidence = dict(row.evidence or {})
    provenance = dict(row.provenance or {})
    strength = "strong" if row.confidence >= 75 else ("medium" if row.confidence >= 55 else "weak")
    return {
        "id":str(row.id),"tenant_id":row.tenant_id,"workspace_id":row.workspace_id,"repository_id":row.repository_id,
        "knowledge_type":row.knowledge_type,"scope":row.scope,"observation":row.observation,"status":row.status,
        "confidence":row.confidence/100.0,"evidence_strength":strength,"evidence":evidence,"provenance":provenance,
        "source_run_id":row.source_run_id,"source_commit":row.source_commit,"fingerprint":row.fingerprint,
        "created_at":row.created_at.isoformat() if row.created_at else None,
        "validated_at":row.validated_at.isoformat() if row.validated_at else None,
    }

@router.post("/candidates", status_code=201)
async def add_candidate(payload: CandidateLearningCreate, db: AsyncSession=Depends(get_db)):
    data=payload.model_dump()
    row=await create_candidate(db,data)
    # Every Agent learning observation is also materialised as a normal OPEN KB entry.
    # It therefore enters the same workstream review/Resolve lifecycle as every other
    # knowledge source and can never become authoritative merely because a run completed.
    from uuid import UUID
    ws_id = None
    if payload.workstream_id:
        try: ws_id = UUID(payload.workstream_id)
        except ValueError: ws_id = None
    owner_scope = payload.scope if payload.scope in {"tenant","workspace","repository"} else "global"
    candidate_entry = Entry(
        entry_type=EntryType.EXAMPLE if payload.knowledge_type == "example" else EntryType.DOCUMENTATION,
        component_name=ComponentName.INGESTION,
        title=f"Agent learning candidate · {payload.knowledge_type} · {payload.project_run_id[:12]}",
        content=payload.observation,
        source=f"agent-run:{payload.project_run_id}:{row.id}",
        author="Kaiwora Agent Learning",
        status=EntryStatus.OPEN,
        embedding=None,
        workstream_id=ws_id,
        owner_scope=owner_scope,
        tenant_id=payload.tenant_id if owner_scope != "global" else None,
        workspace_id=payload.workspace_id if owner_scope in {"workspace","repository"} else None,
        repository_id=payload.repository_id if owner_scope == "repository" else None,
    )
    db.add(candidate_entry)
    await db.commit(); await db.refresh(candidate_entry)
    global_candidate=await maybe_create_global_candidate(db,row,contribution_enabled=payload.global_learning_contribution)
    result=view(row)
    result["workstream_entry_id"] = str(candidate_entry.id)
    result["global_candidate_id"] = str(global_candidate.id) if global_candidate else None
    return result

class CandidateReview(BaseModel):
    model_config=ConfigDict(extra="forbid")
    decision: str = Field(pattern="^(approved|rejected|deferred)$")
    reviewer: str = Field(default="Customer Engineering Admin", min_length=1, max_length=255)
    edited_observation: str | None = Field(default=None, max_length=100_000)
    scope: str | None = Field(default=None, pattern="^(repository|workspace|tenant)$")


@router.get("/candidates")
async def list_candidates(
    tenant_id: str = Query("default"),
    status: str = Query("candidate"),
    workspace_id: str | None = Query(None),
    repository_id: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(LearningEntryDB).where(LearningEntryDB.tenant_id == tenant_id)
    if status != "all": stmt = stmt.where(LearningEntryDB.status == status)
    if workspace_id: stmt = stmt.where(LearningEntryDB.workspace_id == workspace_id)
    if repository_id: stmt = stmt.where(LearningEntryDB.repository_id == repository_id)
    rows=list((await db.execute(stmt.order_by(LearningEntryDB.created_at.desc()).limit(limit))).scalars().all())
    return {"items":[view(r) for r in rows],"count":len(rows)}


@router.post("/candidates/{candidate_id}/review")
async def review_candidate(
    candidate_id: str,
    payload: CandidateReview,
    tenant_id: str = Query("default"),
    db: AsyncSession = Depends(get_db),
    embedder: EmbeddingService = Depends(get_embedding_service),
):
    from datetime import datetime, UTC
    from uuid import UUID
    try: cid=UUID(candidate_id)
    except ValueError as exc: raise HTTPException(422, "Invalid candidate id") from exc
    row=await db.get(LearningEntryDB,cid)
    if row is None or row.tenant_id != tenant_id: raise HTTPException(404,"Learning candidate not found")
    if row.status != "candidate": raise HTTPException(409,"Learning candidate has already been reviewed")

    observation=(payload.edited_observation or row.observation).strip()
    scope=payload.scope or row.scope
    now=datetime.now(UTC)
    entry=(await db.execute(select(Entry).where(Entry.source == f"agent-run:{row.source_run_id}:{row.id}"))).scalar_one_or_none()

    if payload.decision == "approved":
        row.status="validated"; row.validated_at=now; row.observation=observation; row.scope=scope
        ev=dict(row.evidence or {}); ev.update({"human_approved":True,"approved_by":payload.reviewer,"approved_at":now.isoformat()}); row.evidence=ev
        if entry is None:
            entry=Entry(entry_type=EntryType.DOCUMENTATION,component_name=ComponentName.INGESTION,title=f"Approved learning · {row.knowledge_type} · {row.source_run_id[:12]}",content=observation,source=f"agent-run:{row.source_run_id}:{row.id}",author=payload.reviewer,status=EntryStatus.RESOLVED,embedding=None,owner_scope=scope,tenant_id=row.tenant_id,workspace_id=row.workspace_id if scope in {"workspace","repository"} else None,repository_id=row.repository_id if scope=="repository" else None)
            db.add(entry)
        else:
            entry.title=f"Approved learning · {row.knowledge_type} · {row.source_run_id[:12]}"
            entry.content=observation; entry.author=payload.reviewer; entry.status=EntryStatus.RESOLVED; entry.owner_scope=scope
            entry.tenant_id=row.tenant_id; entry.workspace_id=row.workspace_id if scope in {"workspace","repository"} else None; entry.repository_id=row.repository_id if scope=="repository" else None
        try: entry.embedding=await embedder.embed_text(observation)
        except Exception: entry.embedding=None
    else:
        row.status=payload.decision
        ev=dict(row.evidence or {}); ev.update({"human_approved":False,"review_decision":payload.decision,"reviewed_by":payload.reviewer,"reviewed_at":now.isoformat()}); row.evidence=ev
        if entry is not None:
            entry.status=EntryStatus.REJECTED if payload.decision=="rejected" else EntryStatus.DEFERRED
            entry.author=payload.reviewer
    await db.commit(); await db.refresh(row)
    result=view(row); result["approved_entry_id"]=str(entry.id) if entry is not None and entry.id else None
    return result


@router.get("/approved")
async def approved_customer_knowledge(
    tenant_id: str = Query("default"),
    workspace_id: str | None = Query(None),
    repository_id: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    stmt=select(Entry).where(Entry.status==EntryStatus.RESOLVED, Entry.tenant_id==tenant_id)
    if repository_id:
        stmt=stmt.where((Entry.owner_scope!='repository') | (Entry.repository_id==repository_id))
    if workspace_id:
        stmt=stmt.where((Entry.owner_scope=='tenant') | (Entry.workspace_id==workspace_id))
    rows=list((await db.execute(stmt.order_by(Entry.updated_at.desc()).limit(limit))).scalars().all())
    items=[{
        "id":str(r.id),"title":r.title,"content":r.content,"type":r.entry_type.value if hasattr(r.entry_type,"value") else str(r.entry_type),
        "component":r.component_name.value if hasattr(r.component_name,"value") else str(r.component_name),"status":r.status.value if hasattr(r.status,"value") else str(r.status),
        "owner_scope":r.owner_scope,"tenant_id":r.tenant_id,"workspace_id":r.workspace_id,"repository_id":r.repository_id,
        "knowledge_kind":r.knowledge_kind,"applies_to":r.applies_to,"priority":r.priority,"source":r.source,"author":r.author,
    } for r in rows]
    return {"items":items,"count":len(items)}


@router.get("/reusable")
async def get_reusable(tenant_id:str=Query("default"), workspace_id:str=Query("default"), repository_id:str=Query(""), db:AsyncSession=Depends(get_db)):
    return {"entries":[view(r) for r in await reusable(db,tenant_id,workspace_id,repository_id)]}

@router.get('/intelligence')
async def learning_intelligence(tenant_id:str=Query('default'), db:AsyncSession=Depends(get_db)):
    from sqlalchemy import select
    from app.persistence.models import LearningEntryDB
    rows=list((await db.execute(select(LearningEntryDB).where(LearningEntryDB.tenant_id==tenant_id))).scalars().all())
    by_type={}; success=fail=0
    for r in rows:
        by_type[r.knowledge_type]=by_type.get(r.knowledge_type,0)+1
        ev=r.evidence or {}; success+=int(bool(ev.get('run_success'))); fail+=int(not bool(ev.get('run_success')))
    return {'candidate_count':len(rows),'successful_run_signals':success,'failure_run_signals':fail,'by_knowledge_type':by_type,'dimensions':['requirement_intelligence','repository_pattern','context_selection','failure_pattern','repair_playbook','validation_knowledge','tool_knowledge','governance_policy']}

class KnowledgeUsageCreate(BaseModel):
    tenant_id:str; workspace_id:str='default'; repository_id:str=''; run_id:str; entry_ids:list[str]; outcome:str; repair_count:int=0; task_type:str='engineering'; relevance:int=Field(default=80,ge=0,le=100)

@router.post('/knowledge-usage', status_code=201)
async def knowledge_usage(payload:KnowledgeUsageCreate, db:AsyncSession=Depends(get_db)):
    from uuid import UUID
    from app.persistence.models import KnowledgeUsageDB
    count=0
    for raw in payload.entry_ids[:100]:
        try: eid=UUID(raw)
        except ValueError: continue
        db.add(KnowledgeUsageDB(entry_id=eid,tenant_id=payload.tenant_id,workspace_id=payload.workspace_id,repository_id=payload.repository_id,run_id=payload.run_id,task_type=payload.task_type,outcome=payload.outcome,repair_count=max(0,payload.repair_count),relevance=payload.relevance)); count+=1
    await db.commit(); return {'recorded':count}
