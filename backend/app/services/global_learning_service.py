from __future__ import annotations
import hashlib, re
from datetime import datetime, UTC
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.persistence.models import GlobalLearningCandidateDB, LearningEntryDB, Entry, EntryType, ComponentName, EntryStatus

READY='ready_for_review'; APPROVED='approved'; REJECTED='rejected'; DEFERRED='deferred'

def sanitise_observation(text: str) -> str:
    value=' '.join(str(text or '').split())
    value=re.sub(r'https?://\S+', '[url]', value)
    value=re.sub(r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', '[email]', value, flags=re.I)
    value=re.sub(r'(?<![A-Za-z0-9_])(?:[A-Za-z0-9_.-]+/){1,}[A-Za-z0-9_.-]+', '[repository-path]', value)
    value=re.sub(r'\b[0-9a-f]{32,64}\b', '[hash]', value, flags=re.I)
    value=re.sub(r'\b[0-9a-f]{8}-[0-9a-f-]{27,}\b', '[id]', value, flags=re.I)
    return value[:4000]

def global_fingerprint(knowledge_type: str, observation: str) -> str:
    norm=re.sub(r'\s+', ' ', observation.strip().lower())
    return hashlib.sha256(f'{knowledge_type}|{norm}'.encode()).hexdigest()

async def maybe_create_global_candidate(db: AsyncSession, learning: LearningEntryDB, *, contribution_enabled: bool) -> GlobalLearningCandidateDB | None:
    if not contribution_enabled or learning.confidence < 80:
        return None
    evidence=learning.evidence or {}
    validation=evidence.get('final_validation') or {}
    if not bool(evidence.get('run_success')) or validation.get('ok', True) is not True:
        return None
    sanitised=sanitise_observation(learning.observation)
    if not sanitised or sanitised == 'Governed execution outcome':
        return None
    fp=global_fingerprint(learning.knowledge_type, sanitised)
    existing=(await db.execute(select(GlobalLearningCandidateDB).where(
        GlobalLearningCandidateDB.source_learning_entry_id == learning.id
    ))).scalar_one_or_none()
    if existing: return existing
    row=GlobalLearningCandidateDB(
        source_learning_entry_id=learning.id, source_tenant_id=learning.tenant_id,
        source_workspace_id=learning.workspace_id, source_repository_id=learning.repository_id,
        knowledge_type=learning.knowledge_type, sanitised_observation=sanitised, fingerprint=fp,
        confidence=learning.confidence,
        evidence_summary={
            'run_success': bool(evidence.get('run_success')),
            'final_validation_ok': bool(validation.get('ok', evidence.get('run_success'))),
            'acceptance_criteria_count': len((evidence.get('ac_validation_plan') or {}).get('items') or []),
            'validation_event_count': len(evidence.get('validation_history') or []),
            'changed_file_count': len(evidence.get('changed_files') or []),
        },
    )
    db.add(row); await db.commit(); await db.refresh(row); return row

async def list_candidates(db: AsyncSession, status: str=READY, limit: int=100):
    stmt=select(GlobalLearningCandidateDB).where(GlobalLearningCandidateDB.review_status == status).order_by(GlobalLearningCandidateDB.created_at.desc()).limit(limit)
    return list((await db.execute(stmt)).scalars().all())

async def review_candidate(db: AsyncSession, candidate_id, *, decision: str, reviewer: str, note: str=''):
    row=await db.get(GlobalLearningCandidateDB, candidate_id)
    if row is None: return None
    if decision not in {APPROVED, REJECTED, DEFERRED}: raise ValueError('Unsupported review decision')
    if row.review_status == APPROVED and decision != APPROVED: raise ValueError('Approved candidate is immutable; supersede the Master KB entry instead')
    if decision == APPROVED and row.approved_entry_id is None:
        entry=Entry(
            entry_type=EntryType.CONSTRAINT if row.knowledge_type in {'constraint','policy'} else EntryType.DOCUMENTATION,
            component_name=ComponentName.UNKNOWN,
            title=f'Kaiwora validated learning {str(row.id)[:8]}', content=row.sanitised_observation,
            source=f'kaiwora-global-learning:{row.id}', author=reviewer or 'kaiwora-admin',
            owner_scope='global', tenant_id=None, workspace_id=None, repository_id=None,
            status=EntryStatus.RESOLVED, embedding=None, workstream_id=None,
        )
        db.add(entry); await db.flush(); row.approved_entry_id=entry.id
    row.review_status=decision; row.reviewed_by=reviewer; row.review_note=note; row.reviewed_at=datetime.now(UTC)
    await db.commit(); await db.refresh(row); return row


async def create_global_candidate_from_validated(db: AsyncSession, learning: LearningEntryDB) -> GlobalLearningCandidateDB | None:
    """Create a Kaiwora-master review candidate only after customer approval.

    This is intentionally separate from candidate creation: a tenant observation or
    uploaded source must never leave the tenant merely because it was generated.
    """
    if learning.status != 'validated':
        return None
    evidence=learning.evidence or {}
    if not bool(evidence.get('human_approved')):
        return None
    sanitised=sanitise_observation(learning.observation)
    if not sanitised or sanitised == 'Governed execution outcome':
        return None
    existing=(await db.execute(select(GlobalLearningCandidateDB).where(
        GlobalLearningCandidateDB.source_learning_entry_id == learning.id
    ))).scalar_one_or_none()
    if existing:
        return existing
    fp=global_fingerprint(learning.knowledge_type, sanitised)
    validation=evidence.get('final_validation') or {}
    row=GlobalLearningCandidateDB(
        source_learning_entry_id=learning.id, source_tenant_id=learning.tenant_id,
        source_workspace_id=learning.workspace_id, source_repository_id=learning.repository_id,
        knowledge_type=learning.knowledge_type, sanitised_observation=sanitised, fingerprint=fp,
        confidence=max(int(learning.confidence or 0), 80),
        evidence_summary={
            'customer_approved': True,
            'source_kind': (learning.provenance or {}).get('source',''),
            'run_success': bool(evidence.get('run_success')),
            'final_validation_ok': bool(validation.get('ok', evidence.get('run_success', False))),
            'customer_uploaded_source': bool(evidence.get('customer_uploaded_source')),
            'validation_event_count': len(evidence.get('validation_history') or []),
        },
    )
    db.add(row); await db.commit(); await db.refresh(row); return row
