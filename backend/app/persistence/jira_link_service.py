"""Link KB entries to Jira issues and enrich with live metadata."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.persistence.jira_client import (
    JiraClient,
    JiraClientError,
    JiraIssueNotFoundError,
    JiraNotConfiguredError,
    get_jira_client,
    is_jira_configured,
    normalize_jira_key,
)
from app.persistence.models import Entry, EntryJiraLink
from app.persistence.schemas import JiraChildIssueResponse, JiraLinkCreate, JiraLinkResponse, JiraLinksListResponse

logger = logging.getLogger(__name__)


class EntryNotFoundError(Exception):
    """Raised when no entry exists for the given id."""


class JiraLinkNotFoundError(Exception):
    """Raised when the entry has no link for the given Jira key."""


class JiraLinkAlreadyExistsError(Exception):
    """Raised when the entry is already linked to the Jira key."""


async def _get_entry(db: AsyncSession, entry_id: UUID) -> Entry | None:
    result = await db.execute(select(Entry).where(Entry.id == entry_id))
    return result.scalar_one_or_none()


async def _enrich_link(
    jira_key: str,
    *,
    jira: JiraClient,
) -> JiraLinkResponse:
    if not is_jira_configured():
        return JiraLinkResponse(
            jira_key=jira_key,
            title=None,
            status=None,
            issue_type=None,
            story_points=None,
            browse_url=None,
            is_epic=False,
            child_issues=[],
            enrichment_error="Jira is not configured",
        )

    try:
        details = await jira.get_issue(jira_key)
    except JiraIssueNotFoundError:
        return JiraLinkResponse(
            jira_key=jira_key,
            title=None,
            status=None,
            issue_type=None,
            story_points=None,
            browse_url=jira.browse_url(jira_key),
            is_epic=False,
            child_issues=[],
            enrichment_error="Jira issue not found",
        )
    except JiraClientError as exc:
        return JiraLinkResponse(
            jira_key=jira_key,
            title=None,
            status=None,
            issue_type=None,
            story_points=None,
            browse_url=jira.browse_url(jira_key),
            is_epic=False,
            child_issues=[],
            enrichment_error=str(exc),
        )

    return JiraLinkResponse(
        jira_key=details.key,
        title=details.title,
        status=details.status,
        issue_type=details.issue_type,
        story_points=details.story_points,
        browse_url=details.browse_url,
        is_epic=details.is_epic,
        child_issues=[
            JiraChildIssueResponse(
                key=child.key,
                title=child.title,
                status=child.status,
                story_points=child.story_points,
                browse_url=child.browse_url,
            )
            for child in details.child_issues
        ],
        enrichment_error=None,
    )


async def list_jira_links(
    db: AsyncSession,
    entry_id: UUID,
    *,
    jira: JiraClient | None = None,
) -> JiraLinksListResponse:
    client = jira or get_jira_client()
    result = await db.execute(
        select(Entry)
        .where(Entry.id == entry_id)
        .options(selectinload(Entry.jira_links))
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise EntryNotFoundError(str(entry_id))

    links: list[JiraLinkResponse] = []
    for link in entry.jira_links:
        links.append(await _enrich_link(link.jira_key, jira=client))

    return JiraLinksListResponse(entry_id=entry_id, links=links, count=len(links))


async def add_jira_link(
    db: AsyncSession,
    entry_id: UUID,
    data: JiraLinkCreate,
    *,
    jira: JiraClient | None = None,
) -> JiraLinkResponse:
    client = jira or get_jira_client()
    try:
        jira_key = normalize_jira_key(data.jira_key)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    if is_jira_configured():
        try:
            await client.get_issue(jira_key)
        except JiraIssueNotFoundError as exc:
            raise ValueError(f"Jira issue not found: {jira_key}") from exc
        except JiraNotConfiguredError:
            pass
        except JiraClientError as exc:
            raise ValueError("Unable to verify Jira issue; try again later") from exc

    result = await db.execute(
        select(Entry)
        .where(Entry.id == entry_id)
        .options(selectinload(Entry.jira_links))
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise EntryNotFoundError(str(entry_id))

    if any(link.jira_key == jira_key for link in entry.jira_links):
        raise JiraLinkAlreadyExistsError(jira_key)

    link = EntryJiraLink(entry_id=entry_id, jira_key=jira_key)
    db.add(link)
    try:
        await db.commit()
        await db.refresh(link)
    except Exception:
        await db.rollback()
        logger.exception("Failed to add Jira link for entry_id=%s", entry_id)
        raise

    return await _enrich_link(jira_key, jira=client)


async def remove_jira_link(
    db: AsyncSession,
    entry_id: UUID,
    jira_key: str,
) -> None:
    key = normalize_jira_key(jira_key)
    result = await db.execute(
        select(EntryJiraLink).where(
            EntryJiraLink.entry_id == entry_id,
            EntryJiraLink.jira_key == key,
        )
    )
    link = result.scalar_one_or_none()
    if link is None:
        raise JiraLinkNotFoundError(key)

    await db.delete(link)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception("Failed to remove Jira link entry_id=%s key=%s", entry_id, key)
        raise
