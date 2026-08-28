"""Kaiwora Cloud tenancy registry. Internal service-to-service API only."""
from __future__ import annotations
import os, secrets
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.persistence.database import get_db
from app.persistence.models import TenantDB, CloudWorkspaceDB, CloudRepositoryDB

router=APIRouter(prefix='/api/internal/cloud',tags=['cloud-tenancy'])

def require_service(x_kaiwora_service_key:str|None=Header(default=None)):
    expected=os.getenv('KAIWORA_SERVICE_API_KEY','').strip()
    if not expected or not x_kaiwora_service_key or not secrets.compare_digest(expected,x_kaiwora_service_key):
        raise HTTPException(403,'Kaiwora service credentials required')

class TenantCreate(BaseModel):
    model_config=ConfigDict(extra='forbid'); id:UUID|None=None; name:str=Field(min_length=1,max_length=255); slug:str=Field(min_length=1,max_length=255)
class WorkspaceCreate(BaseModel):
    model_config=ConfigDict(extra='forbid'); id:UUID|None=None; tenant_id:UUID; name:str=Field(min_length=1,max_length=255); slug:str=Field(min_length=1,max_length=255)
class RepositoryCreate(BaseModel):
    model_config=ConfigDict(extra='forbid'); id:UUID|None=None; tenant_id:UUID; workspace_id:UUID; external_id:str=Field(min_length=1,max_length=500); name:str=Field(min_length=1,max_length=300); url:str=Field(min_length=1,max_length=2000); default_branch:str=Field(default='main',min_length=1,max_length=300)

def _tenant_view(r): return {'id':str(r.id),'name':r.name,'slug':r.slug,'status':r.status}
def _workspace_view(r): return {'id':str(r.id),'tenant_id':str(r.tenant_id),'name':r.name,'slug':r.slug,'status':r.status}
def _repo_view(r): return {'id':str(r.id),'tenant_id':str(r.tenant_id),'workspace_id':str(r.workspace_id),'external_id':r.external_id,'name':r.name,'url':r.url,'default_branch':r.default_branch,'status':r.status}

@router.post('/tenants',status_code=201,dependencies=[Depends(require_service)])
async def create_tenant(payload:TenantCreate,db:AsyncSession=Depends(get_db)):
    if payload.id and (existing:=await db.get(TenantDB,payload.id)): return _tenant_view(existing)
    row=TenantDB(id=payload.id,name=payload.name.strip(),slug=payload.slug.strip().lower()); db.add(row); await db.commit(); await db.refresh(row); return _tenant_view(row)
@router.post('/workspaces',status_code=201,dependencies=[Depends(require_service)])
async def create_workspace(payload:WorkspaceCreate,db:AsyncSession=Depends(get_db)):
    if await db.get(TenantDB,payload.tenant_id) is None: raise HTTPException(404,'Tenant not found')
    if payload.id and (existing:=await db.get(CloudWorkspaceDB,payload.id)): return _workspace_view(existing)
    row=CloudWorkspaceDB(id=payload.id,tenant_id=payload.tenant_id,name=payload.name.strip(),slug=payload.slug.strip().lower()); db.add(row); await db.commit(); await db.refresh(row); return _workspace_view(row)
@router.post('/repositories',status_code=201,dependencies=[Depends(require_service)])
async def create_repository(payload:RepositoryCreate,db:AsyncSession=Depends(get_db)):
    workspace=await db.get(CloudWorkspaceDB,payload.workspace_id)
    if workspace is None or workspace.tenant_id!=payload.tenant_id: raise HTTPException(404,'Workspace not found for tenant')
    if payload.id and (existing:=await db.get(CloudRepositoryDB,payload.id)): return _repo_view(existing)
    row=CloudRepositoryDB(id=payload.id,tenant_id=payload.tenant_id,workspace_id=payload.workspace_id,external_id=payload.external_id.strip(),name=payload.name.strip(),url=payload.url.strip(),default_branch=payload.default_branch.strip()); db.add(row); await db.commit(); await db.refresh(row); return _repo_view(row)
@router.get('/tenants/{tenant_id}/workspaces',dependencies=[Depends(require_service)])
async def list_workspaces(tenant_id:UUID,db:AsyncSession=Depends(get_db)):
    rows=list((await db.execute(select(CloudWorkspaceDB).where(CloudWorkspaceDB.tenant_id==tenant_id).order_by(CloudWorkspaceDB.created_at))).scalars().all()); return {'items':[_workspace_view(r) for r in rows]}
@router.get('/workspaces/{workspace_id}/repositories',dependencies=[Depends(require_service)])
async def list_repositories(workspace_id:UUID,tenant_id:UUID,db:AsyncSession=Depends(get_db)):
    rows=list((await db.execute(select(CloudRepositoryDB).where(CloudRepositoryDB.workspace_id==workspace_id,CloudRepositoryDB.tenant_id==tenant_id).order_by(CloudRepositoryDB.created_at))).scalars().all()); return {'items':[_repo_view(r) for r in rows]}
