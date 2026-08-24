"""LLM usage tracking — record token consumption and serve aggregate summaries."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.database import get_db
from app.persistence.llm_service import LLMUsageData
from app.persistence.models import LLMUsage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# Qwen 3 235B on AWS Bedrock pricing (USD per token)
INPUT_COST_PER_TOKEN = 0.29 / 1_000_000
OUTPUT_COST_PER_TOKEN = 1.16 / 1_000_000


class UsageSummaryResponse(BaseModel):
    """Aggregate token usage and estimated cost."""

    total_input_tokens: int
    total_output_tokens: int
    total_calls: int
    estimated_cost_usd: float


async def record_usage(
    db: AsyncSession,
    route: str,
    model_id: str,
    usage: LLMUsageData,
) -> None:
    """Insert a single LLM usage record."""
    row = LLMUsage(
        route=route,
        model_id=model_id,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
    )
    db.add(row)
    await db.commit()


@router.get(
    "/llm-usage/summary",
    response_model=UsageSummaryResponse,
    summary="Get aggregate LLM token usage and estimated cost",
)
async def get_usage_summary(
    db: AsyncSession = Depends(get_db),
) -> UsageSummaryResponse:
    stmt = select(
        func.coalesce(func.sum(LLMUsage.input_tokens), 0).label("input_total"),
        func.coalesce(func.sum(LLMUsage.output_tokens), 0).label("output_total"),
        func.count().label("call_count"),
    )
    row = (await db.execute(stmt)).one()

    input_total: int = row.input_total
    output_total: int = row.output_total
    cost = (input_total * INPUT_COST_PER_TOKEN) + (output_total * OUTPUT_COST_PER_TOKEN)

    return UsageSummaryResponse(
        total_input_tokens=input_total,
        total_output_tokens=output_total,
        total_calls=row.call_count,
        estimated_cost_usd=round(cost, 6),
    )
