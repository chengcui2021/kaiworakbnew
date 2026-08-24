"""Jira Cloud REST API client for issue metadata."""

from __future__ import annotations

import base64
import logging
import re
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.persistence.database import settings

logger = logging.getLogger(__name__)

JIRA_KEY_PATTERN = re.compile(r"^[A-Z][A-Z0-9]+-\d+$")

# Story-point custom fields vary by Jira site; request and parse all known candidates.
STORY_POINTS_FIELD_CANDIDATES: tuple[str, ...] = (
    "customfield_10016",
    "customfield_10028",
    "customfield_10110",
    "customfield_10153",
    "customfield_10147",
)


class JiraNotConfiguredError(Exception):
    """Raised when Jira credentials or base URL are missing."""


class JiraIssueNotFoundError(Exception):
    """Raised when Jira returns 404 for an issue key."""


class JiraClientError(Exception):
    """Raised for other Jira API failures."""


@dataclass(frozen=True)
class JiraChildIssue:
    key: str
    title: str
    status: str
    story_points: float | None
    browse_url: str


@dataclass(frozen=True)
class JiraIssueDetails:
    key: str
    title: str
    status: str
    issue_type: str
    story_points: float | None
    browse_url: str
    is_epic: bool
    child_issues: list[JiraChildIssue] = field(default_factory=list)


def normalize_jira_key(raw: str) -> str:
    key = raw.strip().upper()
    if not JIRA_KEY_PATTERN.match(key):
        raise ValueError(f"Invalid Jira issue key: {raw!r}")
    return key


def is_jira_configured() -> bool:
    return bool(settings.jira_base_url.strip() and settings.jira_email.strip() and settings.jira_api_token.strip())


class JiraClient:
    """Async client for Jira Cloud REST API v3."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        email: str | None = None,
        api_token: str | None = None,
        story_points_field: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = (base_url if base_url is not None else settings.jira_base_url).rstrip("/")
        self.email = email if email is not None else settings.jira_email
        self.api_token = api_token if api_token is not None else settings.jira_api_token
        self.story_points_field = (
            story_points_field if story_points_field is not None else settings.jira_story_points_field
        )
        self._http = http_client
        self._owns_client = http_client is None

    def _auth_header(self) -> dict[str, str]:
        if not is_jira_configured() and not (self.base_url and self.email and self.api_token):
            raise JiraNotConfiguredError("Jira is not configured")
        token = base64.b64encode(f"{self.email}:{self.api_token}".encode()).decode()
        return {"Authorization": f"Basic {token}", "Accept": "application/json"}

    async def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=20.0)
            self._owns_client = True
        return self._http

    async def aclose(self) -> None:
        if self._owns_client and self._http is not None:
            await self._http.aclose()
            self._http = None

    def browse_url(self, key: str) -> str:
        return f"{self.base_url}/browse/{key}"

    def _story_points_field_ids(self) -> list[str]:
        ids: list[str] = []
        for field_id in (self.story_points_field, *STORY_POINTS_FIELD_CANDIDATES):
            if field_id not in ids:
                ids.append(field_id)
        return ids

    def _story_points(self, fields: dict[str, Any]) -> float | None:
        for field_id in self._story_points_field_ids():
            raw = fields.get(field_id)
            if raw is None:
                continue
            try:
                return float(raw)
            except (TypeError, ValueError):
                continue
        return None

    def _parse_issue(self, payload: dict[str, Any]) -> JiraIssueDetails:
        key = payload["key"]
        fields = payload.get("fields") or {}
        issue_type = ((fields.get("issuetype") or {}).get("name")) or "Issue"
        status = ((fields.get("status") or {}).get("name")) or "Unknown"
        title = fields.get("summary") or key
        is_epic = issue_type.lower() == "epic"
        return JiraIssueDetails(
            key=key,
            title=title,
            status=status,
            issue_type=issue_type,
            story_points=self._story_points(fields),
            browse_url=self.browse_url(key),
            is_epic=is_epic,
        )

    def _parse_child(self, payload: dict[str, Any]) -> JiraChildIssue:
        key = payload["key"]
        fields = payload.get("fields") or {}
        return JiraChildIssue(
            key=key,
            title=fields.get("summary") or key,
            status=((fields.get("status") or {}).get("name")) or "Unknown",
            story_points=self._story_points(fields),
            browse_url=self.browse_url(key),
        )

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        client = await self._client()
        url = f"{self.base_url}{path}"
        headers = {**self._auth_header(), **kwargs.pop("headers", {})}
        try:
            response = await client.request(method, url, headers=headers, **kwargs)
        except httpx.HTTPError as exc:
            logger.exception("Jira HTTP error for %s", path)
            raise JiraClientError("Failed to reach Jira") from exc

        if response.status_code == 404:
            raise JiraIssueNotFoundError(path)
        if response.status_code >= 400:
            logger.warning("Jira API error %s: %s", response.status_code, response.text[:500])
            raise JiraClientError(f"Jira API error ({response.status_code})")

        return response.json()

    async def get_issue(self, issue_key: str) -> JiraIssueDetails:
        key = normalize_jira_key(issue_key)
        fields = ",".join(["summary", "status", "issuetype", *self._story_points_field_ids()])
        payload = await self._request("GET", f"/rest/api/3/issue/{key}", params={"fields": fields})
        details = self._parse_issue(payload)
        if details.is_epic:
            children = await self.get_epic_children(key)
            return JiraIssueDetails(
                key=details.key,
                title=details.title,
                status=details.status,
                issue_type=details.issue_type,
                story_points=details.story_points,
                browse_url=details.browse_url,
                is_epic=True,
                child_issues=children,
            )
        return details

    async def get_epic_children(self, epic_key: str) -> list[JiraChildIssue]:
        key = normalize_jira_key(epic_key)
        jql = f'("Epic Link" = {key} OR parent = {key}) ORDER BY rank'
        payload = await self._request(
            "POST",
            "/rest/api/3/search",
            json={
                "jql": jql,
                "maxResults": 50,
                "fields": ["summary", "status", *self._story_points_field_ids()],
            },
        )
        issues = payload.get("issues") or []
        return [self._parse_child(item) for item in issues]


_jira_client: JiraClient | None = None


def get_jira_client() -> JiraClient:
    global _jira_client
    if _jira_client is None:
        _jira_client = JiraClient()
    return _jira_client
