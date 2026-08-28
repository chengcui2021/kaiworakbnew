from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from app.persistence.database import get_db
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

def view(row):
    return {"id":str(row.id),"tenant_id":row.tenant_id,"workspace_id":row.workspace_id,"repository_id":row.repository_id,"knowledge_type":row.knowledge_type,"scope":row.scope,"observation":row.observation,"status":row.status,"confidence":row.confidence/100.0,"source_run_id":row.source_run_id,"source_commit":row.source_commit,"fingerprint":row.fingerprint,"created_at":row.created_at.isoformat() if row.created_at else None}

@router.post("/candidates", status_code=201)
async def add_candidate(payload: CandidateLearningCreate, db: AsyncSession=Depends(get_db)):
    data=payload.model_dump()
    row=await create_candidate(db,data)
    global_candidate=await maybe_create_global_candidate(db,row,contribution_enabled=payload.global_learning_contribution)
    result=view(row)
    result["global_candidate_id"] = str(global_candidate.id) if global_candidate else None
    return result

@router.get("/reusable")
async def get_reusable(tenant_id:str=Query("default"), workspace_id:str=Query("default"), repository_id:str=Query(""), db:AsyncSession=Depends(get_db)):
    return {"entries":[view(r) for r in await reusable(db,tenant_id,workspace_id,repository_id)]}
