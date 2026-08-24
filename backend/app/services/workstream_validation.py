"""Workstream validation service (PostgreSQL-backed).

Runs a single on-demand check against a workstream to verify that the
reported entry count matches the actual count of stored entries.

Results are computed on demand and are not persisted.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.models import Entry
from app.persistence.workstream_service import get_workstream
from app.schemas.models import ValidationCheck, WorkstreamValidationResult


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _check_statistics(db: AsyncSession, workstream_id: UUID, reported_count: int) -> ValidationCheck:
    """Confirm reported entry_count matches the real stored count."""
    actual = await db.scalar(
        select(func.count()).select_from(Entry).where(Entry.workstream_id == workstream_id)
    )
    actual = int(actual or 0)
    if reported_count != actual:
        return ValidationCheck(
            name="statistics",
            label="Workstream statistics load successfully",
            status="fail",
            message=f"Reported count ({reported_count}) does not match actual count ({actual}).",
            details={"reported": reported_count, "actual": actual},
        )
    return ValidationCheck(
        name="statistics",
        label="Workstream statistics load successfully",
        status="pass",
        message=f"Statistics loaded: {actual} entry(ies) counted correctly.",
        details={"entry_count": actual},
    )


async def validate_workstream(db: AsyncSession, workstream_id: UUID) -> WorkstreamValidationResult:
    ws = await get_workstream(db, workstream_id)
    if ws is None:
        raise KeyError(str(workstream_id))

    checks: list[ValidationCheck] = []
    try:
        checks.append(await _check_statistics(db, workstream_id, ws.entry_count))
    except Exception as exc:
        checks.append(ValidationCheck(
            name="statistics",
            label="Workstream statistics load successfully",
            status="warning",
            message=f"Check could not complete: {exc}",
        ))

    if any(c.status == "fail" for c in checks):
        overall = "fail"
    elif any(c.status == "warning" for c in checks):
        overall = "warning"
    else:
        overall = "pass"

    return WorkstreamValidationResult(
        workstream_id=str(workstream_id),
        workstream_name=ws.name,
        validated_at=_now(),
        overall_status=overall,
        checks=checks,
    )
