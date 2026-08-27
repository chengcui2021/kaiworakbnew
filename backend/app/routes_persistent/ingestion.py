"""Governed knowledge-source ingestion.

GitHub ingestion snapshots an exact commit and creates OPEN candidate knowledge
entries. It deliberately never approves/resolves entries automatically.
"""
from __future__ import annotations

import base64
import fnmatch
import logging
import os
from pathlib import PurePosixPath
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.persistence.constants import EMBEDDING_DIMENSION
from app.persistence.database import get_db
from app.persistence.embeddings import EmbeddingService, get_embedding_service
from app.persistence.entry_response import entry_to_response
from app.persistence.models import ComponentName, Entry, EntryStatus, EntryTag, EntryType
from app.persistence.schemas import EntryResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ingestion", tags=["knowledge-ingestion"])

_TEXT_SUFFIXES = {".md", ".markdown", ".mdown", ".txt", ".rst", ".adoc", ".yaml", ".yml", ".json"}
_MAX_FILES = 40
_MAX_FILE_BYTES = 250_000
_MAX_CANDIDATES = 100


class GitHubIngestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    repository_url: str = Field(..., min_length=1, max_length=2000)
    branch: str = Field(default="main", min_length=1, max_length=255)
    ref: str | None = Field(default=None, max_length=255)
    include_paths: list[str] = Field(default_factory=lambda: ["**/*.md", "*.md", "**/CLAUDE.md", "**/AGENTS.md"], max_length=50)
    exclude_paths: list[str] = Field(default_factory=lambda: ["node_modules/**", "dist/**", "build/**", ".git/**"], max_length=50)
    workstream_id: UUID | None = None
    author: str = Field(default="Knowledge Ingestion", min_length=1, max_length=255)

    @field_validator("repository_url")
    @classmethod
    def validate_repo(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        if value.endswith(".git"):
            value = value[:-4]
        prefix = "https://github.com/"
        if not value.startswith(prefix):
            raise ValueError("Only https://github.com/<owner>/<repository> sources are supported")
        parts = value[len(prefix):].split("/")
        if len(parts) != 2 or not all(parts):
            raise ValueError("Repository URL must be https://github.com/<owner>/<repository>")
        return value


class GitHubIngestionResponse(BaseModel):
    repository_url: str
    branch: str
    commit_sha: str
    scanned_files: int
    candidate_count: int
    candidates: list[EntryResponse]


def _repo_parts(url: str) -> tuple[str, str]:
    owner, repo = url.removeprefix("https://github.com/").split("/", 1)
    return owner, repo


def _matches(path: str, patterns: list[str]) -> bool:
    # fnmatch's ** behaviour varies around root files, so also test basename.
    return any(fnmatch.fnmatch(path, p) or fnmatch.fnmatch(PurePosixPath(path).name, p) for p in patterns)


def _candidate_sections(path: str, text: str) -> list[tuple[str, str]]:
    """Split Markdown by H1/H2 headings; keep other source files as one candidate."""
    suffix = PurePosixPath(path).suffix.lower()
    if suffix not in {".md", ".markdown", ".mdown"}:
        title = PurePosixPath(path).name
        return [(title, text.strip())] if text.strip() else []

    sections: list[tuple[str, list[str]]] = []
    current_title = PurePosixPath(path).stem.replace("-", " ").replace("_", " ").strip()
    current: list[str] = []
    for line in text.splitlines():
        if line.startswith("# ") or line.startswith("## "):
            if any(x.strip() for x in current):
                sections.append((current_title, current))
            current_title = line.lstrip("#").strip() or current_title
            current = []
        else:
            current.append(line)
    if any(x.strip() for x in current):
        sections.append((current_title, current))

    result: list[tuple[str, str]] = []
    for title, lines in sections:
        content = "\n".join(lines).strip()
        if content:
            result.append((title[:255], content[:100_000]))
    return result or [(PurePosixPath(path).stem[:255], text.strip()[:100_000])]


async def _github_json(client: httpx.AsyncClient, url: str) -> dict | list:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = await client.get(url, headers=headers)
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="GitHub repository/ref not found or inaccessible. Configure GITHUB_TOKEN for private repositories.")
    if response.status_code == 403:
        raise HTTPException(status_code=502, detail="GitHub API rate limit reached; try again later")
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"GitHub API returned HTTP {response.status_code}")
    return response.json()


@router.post("/github", response_model=GitHubIngestionResponse, status_code=status.HTTP_201_CREATED)
async def ingest_github(
    data: GitHubIngestionRequest,
    db: AsyncSession = Depends(get_db),
    embedder: EmbeddingService = Depends(get_embedding_service),
) -> GitHubIngestionResponse:
    owner, repo = _repo_parts(data.repository_url)
    requested_ref = (data.ref or data.branch).strip()
    base = f"https://api.github.com/repos/{owner}/{repo}"

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        commit = await _github_json(client, f"{base}/commits/{requested_ref}")
        if not isinstance(commit, dict) or not commit.get("sha"):
            raise HTTPException(status_code=502, detail="GitHub returned an invalid commit response")
        commit_sha = str(commit["sha"])
        tree = await _github_json(client, f"{base}/git/trees/{commit_sha}?recursive=1")
        tree_items = tree.get("tree", []) if isinstance(tree, dict) else []

        paths: list[str] = []
        for item in tree_items:
            if item.get("type") != "blob":
                continue
            path = str(item.get("path") or "")
            size = int(item.get("size") or 0)
            if not path or size > _MAX_FILE_BYTES or PurePosixPath(path).suffix.lower() not in _TEXT_SUFFIXES:
                continue
            if data.include_paths and not _matches(path, data.include_paths):
                continue
            if data.exclude_paths and _matches(path, data.exclude_paths):
                continue
            paths.append(path)
            if len(paths) >= _MAX_FILES:
                break

        # If a previous request reached the database commit but failed while
        # serialising the response, the OPEN candidates already exist. Load
        # candidates from this exact repository snapshot up front so a retry is
        # idempotent rather than creating duplicates.
        source_prefix = f"github:{data.repository_url}@{commit_sha}:"
        existing_result = await db.execute(
            select(Entry)
            .where(
                Entry.status == EntryStatus.OPEN,
                Entry.source.startswith(source_prefix),
            )
            .options(selectinload(Entry.entry_tags).selectinload(EntryTag.tag))
        )
        existing_entries = existing_result.scalars().all()
        existing_by_key = {
            (entry.source or "", entry.title, entry.content): entry
            for entry in existing_entries
        }

        candidates: list[Entry] = []
        for path in paths:
            if len(candidates) >= _MAX_CANDIDATES:
                break
            blob = await _github_json(client, f"{base}/contents/{path}?ref={commit_sha}")
            if not isinstance(blob, dict) or blob.get("encoding") != "base64":
                continue
            try:
                raw = base64.b64decode(str(blob.get("content") or ""), validate=False)
                text = raw.decode("utf-8")
            except (ValueError, UnicodeDecodeError):
                continue

            for title, content in _candidate_sections(path, text):
                if len(candidates) >= _MAX_CANDIDATES:
                    break
                source = f"github:{data.repository_url}@{commit_sha}:{path}"
                existing = existing_by_key.get((source, title, content))
                if existing is not None:
                    candidates.append(existing)
                    continue

                vector = None
                try:
                    vector = await embedder.embed_text(content)
                    if vector is not None and len(vector) != EMBEDDING_DIMENSION:
                        vector = None
                except Exception:
                    logger.warning("Embedding unavailable during GitHub ingestion for %s", path)
                entry = Entry(
                    entry_type=EntryType.DOCUMENTATION,
                    component_name=ComponentName.INGESTION,
                    title=title,
                    content=content,
                    source=source,
                    author=data.author.strip(),
                    status=EntryStatus.OPEN,
                    embedding=vector,
                    workstream_id=data.workstream_id,
                )
                db.add(entry)
                candidates.append(entry)

    try:
        await db.commit()

        # entry_to_response() reads Entry.entry_tags and EntryTag.tag. Those
        # relationships must be loaded explicitly with AsyncSession; otherwise
        # SQLAlchemy attempts an implicit lazy-load during serialisation and
        # raises MissingGreenlet. Re-query every response row with selectinload
        # after commit so response construction performs no database I/O.
        candidate_ids = [entry.id for entry in candidates if entry.id is not None]
        hydrated_candidates: list[Entry] = []
        if candidate_ids:
            hydrated_result = await db.execute(
                select(Entry)
                .where(Entry.id.in_(candidate_ids))
                .options(selectinload(Entry.entry_tags).selectinload(EntryTag.tag))
            )
            hydrated_by_id = {entry.id: entry for entry in hydrated_result.scalars().all()}
            hydrated_candidates = [
                hydrated_by_id[entry.id]
                for entry in candidates
                if entry.id in hydrated_by_id
            ]
    except Exception as exc:
        await db.rollback()
        logger.exception("Failed to persist or hydrate GitHub ingestion candidates")
        raise HTTPException(status_code=500, detail="Failed to persist ingestion candidates") from exc

    return GitHubIngestionResponse(
        repository_url=data.repository_url,
        branch=data.branch,
        commit_sha=commit_sha,
        scanned_files=len(paths),
        candidate_count=len(hydrated_candidates),
        candidates=[entry_to_response(entry) for entry in hydrated_candidates],
    )
