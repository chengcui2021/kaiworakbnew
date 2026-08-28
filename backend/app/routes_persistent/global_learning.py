from __future__ import annotations
import os, secrets
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.persistence.database import get_db
from app.services.global_learning_service import list_candidates, review_candidate

router=APIRouter(prefix='/api/internal/admin/global-learning', tags=['global-learning-admin'])

def require_admin(x_kaiwora_admin_key: str | None = Header(default=None)):
    expected=os.getenv('KAIWORA_ADMIN_API_KEY','').strip()
    if not expected or not x_kaiwora_admin_key or not secrets.compare_digest(expected, x_kaiwora_admin_key):
        raise HTTPException(403, 'Kaiwora admin credentials required')

class ReviewRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    decision: str = Field(pattern='^(approved|rejected|deferred)$')
    reviewer: str = Field(min_length=1, max_length=255)
    note: str = Field(default='', max_length=4000)

def view(r):
    return {'id':str(r.id),'source_learning_entry_id':str(r.source_learning_entry_id),'source_tenant_id':r.source_tenant_id,
            'source_workspace_id':r.source_workspace_id,'source_repository_id':r.source_repository_id,'knowledge_type':r.knowledge_type,
            'sanitised_observation':r.sanitised_observation,'confidence':r.confidence/100.0,'evidence_summary':r.evidence_summary,
            'privacy_status':r.privacy_status,'review_status':r.review_status,'reviewed_by':r.reviewed_by,'review_note':r.review_note,
            'approved_entry_id':str(r.approved_entry_id) if r.approved_entry_id else None,'created_at':r.created_at.isoformat() if r.created_at else None}

@router.get('/candidates', dependencies=[Depends(require_admin)])
async def candidates(status:str=Query('ready_for_review'), limit:int=Query(100,ge=1,le=500), db:AsyncSession=Depends(get_db)):
    return {'items':[view(r) for r in await list_candidates(db,status,limit)]}

@router.post('/candidates/{candidate_id}/review', dependencies=[Depends(require_admin)])
async def review(candidate_id:UUID,payload:ReviewRequest,db:AsyncSession=Depends(get_db)):
    try: row=await review_candidate(db,candidate_id,decision=payload.decision,reviewer=payload.reviewer,note=payload.note)
    except ValueError as exc: raise HTTPException(409,str(exc)) from exc
    if row is None: raise HTTPException(404,'Global learning candidate not found')
    return view(row)
