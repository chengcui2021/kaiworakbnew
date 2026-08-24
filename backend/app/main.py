"""FastAPI application entrypoint for Continue KB Phase 1.5.

Knowledge Base with workspace-scoped search and workspace validation.
Uses in-memory mock data only.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import context_assembly, documents, packages, search, workspaces, workstreams
from app.routes_persistent import entries as persistent_entries, semantic_search as persistent_search, tags as persistent_tags, jira_links as persistent_jira_links, persistence_health, templates as persistent_templates, transform as persistent_transform, llm_usage as persistent_llm_usage, learning as governed_learning

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Continue KB Phase 1.5", version="1.5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(workspaces.router)
app.include_router(workstreams.router)
app.include_router(documents.router)
app.include_router(packages.router)
app.include_router(search.router)
app.include_router(context_assembly.router)
# Persistent KB management console routes restored from MDSU-41.
# persistent_search must be registered before persistent_entries: both define
# a route under /entries, and Starlette matches in registration order, so the
# literal /entries/search must be tried before the catch-all /entries/{entry_id}.
app.include_router(persistence_health.router)
app.include_router(persistent_search.router)
app.include_router(persistent_entries.router)
app.include_router(persistent_tags.router)
app.include_router(persistent_jira_links.router)
app.include_router(persistent_templates.router)
app.include_router(persistent_transform.router)
app.include_router(persistent_llm_usage.router)
app.include_router(governed_learning.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "continue-kb", "version": "1.5.0"}


@app.get("/")
def root() -> dict:
    return {
        "service": "Continue KB Phase 1.5",
        "endpoints": [
            "/health",
            "/api/workspaces",
            "/api/workspaces/{id}/stats",
            "/api/workspaces/{id}/validate",
            "/api/workspaces/{id}/activities?limit=20",
            "/api/workspaces/{id}/documents?approval_status=approved",
            "/api/workspaces/{id}/documents/{doc_id}/move",
            "/api/workspaces/{id}/documents/{doc_id}/status",
            "/api/workspaces/{id}/packages",
            "/api/search?workspace_id=...&q=...",
            "/api/governed-context/assemble",
            "/api/governed-context/lock",
            "/api/governed-context/locks/{lock_id}",
            "/api/governed-context/locks/{lock_id}/status",
            "/api/governed-context/lock/status",
        ],
    }
