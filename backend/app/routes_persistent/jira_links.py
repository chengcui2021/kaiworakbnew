"""Jira connector API — link KB entries to Jira tickets/epics."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.database import get_db
from app.persistence.jira_link_service import (
    EntryNotFoundError,
    JiraLinkAlreadyExistsError,
    JiraLinkNotFoundError,
    add_jira_link,
    list_jira_links,
    remove_jira_link,
)
from app.persistence.schemas import JiraLinkCreate, JiraLinkResponse, JiraLinksListResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


@router.get(
    "/entries/{entry_id}/jira-links",
    response_model=JiraLinksListResponse,
    summary="List Jira links for an entry",
)
async def get_entry_jira_links(
    entry_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> JiraLinksListResponse:
    try:
        return await list_jira_links(db, entry_id)
    except EntryNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found") from None
    except Exception as e:
        logger.exception("Failed to list Jira links")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list Jira links",
        ) from e


@router.post(
    "/entries/{entry_id}/jira-links",
    response_model=JiraLinkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Link a KB entry to a Jira ticket or epic",
)
async def post_entry_jira_link(
    entry_id: UUID,
    data: JiraLinkCreate,
    db: AsyncSession = Depends(get_db),
) -> JiraLinkResponse:
    try:
        return await add_jira_link(db, entry_id, data)
    except EntryNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found") from None
    except JiraLinkAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Entry is already linked to this Jira issue",
        ) from None
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    except Exception as e:
        logger.exception("Failed to add Jira link")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add Jira link",
        ) from e


@router.delete(
    "/entries/{entry_id}/jira-links/{jira_key}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a Jira link from an entry",
)
async def delete_entry_jira_link(
    entry_id: UUID,
    jira_key: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    try:
        await remove_jira_link(db, entry_id, jira_key)
    except JiraLinkNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Jira link not found") from None
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    except Exception as e:
        logger.exception("Failed to remove Jira link")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove Jira link",
        ) from e
