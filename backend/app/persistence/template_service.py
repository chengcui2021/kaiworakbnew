"""Template catalog CRUD operations."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.models import Template
from app.persistence.schemas import TemplateCreate, TemplateResponse, TemplatesListResponse, TemplateUpdate

logger = logging.getLogger(__name__)


class TemplateNotFoundError(Exception):
    """Raised when no template exists for the given id."""


class TemplateAlreadyExistsError(Exception):
    """Raised when a template name is already in the catalog."""


async def _get_template_by_name(db: AsyncSession, name: str) -> Template | None:
    result = await db.execute(select(Template).where(Template.name == name))
    return result.scalar_one_or_none()


async def list_templates(db: AsyncSession) -> TemplatesListResponse:
    templates = (await db.execute(select(Template).order_by(Template.name.asc()))).scalars().all()
    return TemplatesListResponse(
        templates=[TemplateResponse.model_validate(t) for t in templates],
        count=len(templates),
    )


async def get_template(db: AsyncSession, template_id: UUID) -> TemplateResponse:
    result = await db.execute(select(Template).where(Template.id == template_id))
    template = result.scalar_one_or_none()
    if template is None:
        raise TemplateNotFoundError(str(template_id))
    return TemplateResponse.model_validate(template)


async def create_template(db: AsyncSession, data: TemplateCreate) -> TemplateResponse:
    if await _get_template_by_name(db, data.name) is not None:
        raise TemplateAlreadyExistsError(data.name)

    template = Template(name=data.name, content=data.content)
    db.add(template)
    try:
        await db.commit()
        await db.refresh(template)
    except Exception:
        await db.rollback()
        logger.exception("Failed to create template name=%s", data.name)
        raise
    return TemplateResponse.model_validate(template)


async def update_template(
    db: AsyncSession, template_id: UUID, data: TemplateUpdate
) -> TemplateResponse:
    result = await db.execute(select(Template).where(Template.id == template_id))
    template = result.scalar_one_or_none()
    if template is None:
        raise TemplateNotFoundError(str(template_id))

    if data.name != template.name and await _get_template_by_name(db, data.name) is not None:
        raise TemplateAlreadyExistsError(data.name)

    template.name = data.name
    template.content = data.content

    try:
        await db.commit()
        await db.refresh(template)
    except Exception:
        await db.rollback()
        logger.exception("Failed to update template id=%s", template_id)
        raise
    return TemplateResponse.model_validate(template)


async def delete_template(db: AsyncSession, template_id: UUID) -> None:
    result = await db.execute(select(Template).where(Template.id == template_id))
    template = result.scalar_one_or_none()
    if template is None:
        raise TemplateNotFoundError(str(template_id))

    await db.delete(template)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception("Failed to delete template id=%s", template_id)
        raise
