from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from app.persistence.database import get_db
from app.persistence.models import Entry, EntryStatus, EntryType, ComponentName
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
    return {"id":str(row.id),"tenant_id":row.tenant_id,"workspace_id":row.workspace_id,"repository_id":row.repository_id,"knowledge_type":row.knowledge_type,"scope":row.scope,"observation":row.observation,"status":row.status,"confidence":row.confidence/100.0,"source_run_id":row.source_run_id,"source_commit":row.source_commit,"fingerprint":row.fingerprint,"created_at":row.created_at.isoformat() if row.created_at else None}

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
