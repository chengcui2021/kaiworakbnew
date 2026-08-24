"""Template catalog API."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.database import get_db
from app.persistence.schemas import TemplateCreate, TemplateResponse, TemplatesListResponse, TemplateUpdate
from app.persistence.template_service import (
    TemplateAlreadyExistsError,
    TemplateNotFoundError,
    create_template,
    delete_template,
    get_template,
    list_templates,
    update_template,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


@router.get("/templates", response_model=TemplatesListResponse, summary="List all templates")
async def get_templates(db: AsyncSession = Depends(get_db)) -> TemplatesListResponse:
    try:
        return await list_templates(db)
    except Exception as e:
        logger.exception("Failed to list templates")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list templates") from e


@router.get("/templates/{template_id}", response_model=TemplateResponse, summary="Get a template")
async def get_template_route(template_id: UUID, db: AsyncSession = Depends(get_db)) -> TemplateResponse:
    try:
        return await get_template(db, template_id)
    except TemplateNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found") from None
    except Exception as e:
        logger.exception("Failed to get template")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get template") from e


@router.post("/templates", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED, summary="Create a template")
async def post_template(data: TemplateCreate, db: AsyncSession = Depends(get_db)) -> TemplateResponse:
    try:
        return await create_template(db, data)
    except TemplateAlreadyExistsError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Template already exists") from None
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    except Exception as e:
        logger.exception("Failed to create template")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create template") from e


@router.put("/templates/{template_id}", response_model=TemplateResponse, summary="Update a template")
async def put_template(template_id: UUID, data: TemplateUpdate, db: AsyncSession = Depends(get_db)) -> TemplateResponse:
    try:
        return await update_template(db, template_id, data)
    except TemplateNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found") from None
    except TemplateAlreadyExistsError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Template name already in use") from None
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    except Exception as e:
        logger.exception("Failed to update template")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update template") from e


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a template")
async def delete_template_route(template_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    try:
        await delete_template(db, template_id)
    except TemplateNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found") from None
    except Exception as e:
        logger.exception("Failed to delete template")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete template") from e
