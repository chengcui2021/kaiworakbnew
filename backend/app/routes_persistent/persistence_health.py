"""Health and readiness checks."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.database import get_db

router = APIRouter()


@router.get("/health/ready")
async def ready(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Readiness: database has pgvector and the entries schema."""
    ext = await db.scalar(
        text("SELECT 1 FROM pg_extension WHERE extname = 'vector' LIMIT 1")
    )
    if ext is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "PostgreSQL pgvector extension is not installed. "
                "Use image pgvector/pgvector:pg16 and run: alembic upgrade head"
            ),
        )

    try:
        await db.execute(text("SELECT 1 FROM entries LIMIT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Database schema is not ready (entries table missing). "
                "Run: alembic upgrade head"
            ),
        ) from exc

    return {"status": "ready"}
