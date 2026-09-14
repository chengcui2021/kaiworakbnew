"""KB-owned governed engineering analysis using approved knowledge + model gateway.

Agent/Core supplies immutable work-item and repository facts.  This module uses
approved/resolved KB knowledge as authoritative reasoning context and asks the
configured Kaiwora Model Gateway only to derive structured requirement/repository
analysis.  It never grants execution permission; Context Assembly/Lock remains the
governance authority.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx

from app.schemas.context_assembly import (
    RawRequirementInput,
    RepositoryAnalysisInput,
    RepositoryFileInput,
    RepositorySnapshotInput,
    RequirementAnalysisInput,
)

_JSON_RE = re.compile(r"\{.*\}", re.S)
_EXECUTABLE_EXTS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt", ".go", ".rs",
    ".cs", ".rb", ".php", ".swift", ".scala", ".vue", ".svelte",
}
_MANIFESTS = {"package.json", "pyproject.toml", "pom.xml", "build.gradle", "go.mod", "cargo.toml"}


class GovernedAnalysisError(RuntimeError):
    pass


def _gateway_settings() -> tuple[str, str, str, float]:
    base = (os.getenv("GOVERNED_ANALYSIS_BASE_URL") or os.getenv("LOCAL_EMBEDDING_BASE_URL") or "").rstrip("/")
    key = os.getenv("GOVERNED_ANALYSIS_API_KEY") or os.getenv("LOCAL_EMBEDDING_API_KEY") or ""
    model = os.getenv("GOVERNED_ANALYSIS_MODEL") or "qwen3-coder:30b"
    timeout = float(os.getenv("GOVERNED_ANALYSIS_TIMEOUT_SECONDS", "120") or "120")
    if not base:
        raise GovernedAnalysisError("GOVERNED_ANALYSIS_BASE_URL is not configured")
    return base, key, model, timeout


def _bootstrap(snapshot: RepositorySnapshotInput) -> bool:
    for item in snapshot.files:
        lower = item.path.casefold()
        if any(lower.endswith(ext) for ext in _EXECUTABLE_EXTS):
            return False
        if lower.rsplit("/", 1)[-1] in _MANIFESTS:
            return False
    return True


def seed_analysis(requirement: RawRequirementInput, snapshot: RepositorySnapshotInput) -> tuple[RequirementAnalysisInput, RepositoryAnalysisInput]:
    """Create retrieval-only factual seed; this is not model interpretation."""
    bootstrap = _bootstrap(snapshot)
    files = [
        RepositoryFileInput(
            path=x.path,
            language=x.language,
            role=x.role,
            context_role="verification" if x.path.casefold().endswith((".md", ".txt")) else "implementation",
            access="read_only" if x.path.casefold().endswith((".md", ".txt")) else "read_write",
        )
        for x in snapshot.files[:200]
    ]
    req = RequirementAnalysisInput(
        request_id=requirement.request_id,
        title=requirement.title,
        description=requirement.description,
        acceptance_criteria=requirement.acceptance_criteria,
        source=requirement.source or "agent_work_item",
    )
    repo = RepositoryAnalysisInput(
        name=snapshot.name,
        url=snapshot.url,
        branch=snapshot.branch,
        commit_sha=snapshot.commit_sha,
        relevant_files=files,
        impacted_components=[],
        dependencies=[],
        architecture_context=["bootstrap_project" if bootstrap else "existing_application"],
        analysis_evidence=[
            f"snapshot_file_count={len(snapshot.files)}",
            f"bootstrap_project={str(bootstrap).lower()}",
            "evidence_source=agent_repository_snapshot",
            *snapshot.evidence[:30],
        ],
    )
    return req, repo


def _extract_json(text: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
    except Exception:
        pass
    match = _JSON_RE.search(text or "")
    if not match:
        raise GovernedAnalysisError("Governed analysis model returned no JSON object")
    try:
        value = json.loads(match.group(0))
    except Exception as exc:
        raise GovernedAnalysisError("Governed analysis model returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise GovernedAnalysisError("Governed analysis model returned invalid object")
    return value


async def analyse_with_approved_knowledge(
    requirement: RawRequirementInput,
    snapshot: RepositorySnapshotInput,
    approved_knowledge: list[dict[str, Any]],
) -> tuple[RequirementAnalysisInput, RepositoryAnalysisInput, dict[str, Any]]:
    base, key, model, timeout = _gateway_settings()
    bootstrap = _bootstrap(snapshot)
    inventory = [
        {
            "path": x.path,
            "language": x.language,
            "size": x.size,
            "role": x.role,
            "excerpt": (x.excerpt or "")[:1200],
        }
        for x in snapshot.files[:160]
    ]
    knowledge = [
        {
            "entry_id": x.get("entry_id"),
            "title": x.get("title"),
            "content": str(x.get("content") or "")[:5000],
            "source": x.get("source"),
            "scope": x.get("scope"),
            "knowledge_kind": x.get("knowledge_kind"),
            "owner_scope": x.get("owner_scope"),
            "applies_to": x.get("applies_to"),
            "priority": x.get("priority"),
        }
        for x in approved_knowledge[:20]
    ]
    prompt = f"""You are the governed engineering analysis engine inside Kaiwora KB.
Approved/resolved KB knowledge below is authoritative guidance. Repository inventory is immutable evidence.
Do NOT invent existing files. For a sparse/greenfield repository, explicitly classify bootstrap_project and describe
what may need to be created as architecture_context; do not pretend proposed files already exist.
Return strict JSON with keys requirement_analysis and repository_analysis only.

RAW REQUIREMENT:\n{json.dumps(requirement.model_dump(mode='json'), ensure_ascii=False)}

REPOSITORY SNAPSHOT (bootstrap_detected={str(bootstrap).lower()}):\n{json.dumps({'name':snapshot.name,'url':snapshot.url,'branch':snapshot.branch,'commit_sha':snapshot.commit_sha,'files':inventory,'top_level_paths':snapshot.top_level_paths,'evidence':snapshot.evidence}, ensure_ascii=False)[:28000]}

APPROVED / RESOLVED KNOWLEDGE:\n{json.dumps(knowledge, ensure_ascii=False)[:30000]}

Required JSON schema:
{{
  "requirement_analysis": {{
    "request_id":"...", "title":"...", "description":"...", "acceptance_criteria":[],
    "clarified_requirement":"...", "constraints":[], "assumptions":[], "ambiguities":[], "dependencies":[], "source":"kb_governed_analysis"
  }},
  "repository_analysis": {{
    "name":"...", "url":"...", "branch":"...", "commit_sha":"...",
    "relevant_files":[{{"path":"EXISTING_PATH_ONLY","language":null,"role":null,"context_role":"implementation|verification","access":"read_write|read_only"}}],
    "impacted_components":[], "dependencies":[], "architecture_context":[], "analysis_evidence":[]
  }}
}}
"""
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Return strict JSON only. Approved KB knowledge is authoritative; repository snapshot is factual."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "max_tokens": 5000,
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(f"{base}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            body = response.json()
    except Exception as exc:
        raise GovernedAnalysisError(f"Governed analysis model gateway request failed: {exc}") from exc
    try:
        content = body["choices"][0]["message"]["content"]
    except Exception as exc:
        raise GovernedAnalysisError("Governed analysis gateway returned an unexpected response") from exc
    data = _extract_json(str(content or ""))

    req_data = dict(data.get("requirement_analysis") or {})
    repo_data = dict(data.get("repository_analysis") or {})
    # Immutable identity always comes from trusted Agent facts, never the model.
    req_data.update({
        "request_id": requirement.request_id,
        "title": requirement.title,
        "description": requirement.description,
        "acceptance_criteria": requirement.acceptance_criteria,
        "source": requirement.source or "kb_governed_analysis",
    })
    repo_data.update({
        "name": snapshot.name,
        "url": snapshot.url,
        "branch": snapshot.branch,
        "commit_sha": snapshot.commit_sha,
    })
    existing = {x.path: x for x in snapshot.files}
    safe_relevant = []
    for raw in repo_data.get("relevant_files") or []:
        if not isinstance(raw, dict):
            continue
        path = str(raw.get("path") or "").strip()
        if path not in existing:
            continue
        meta = existing[path]
        safe_relevant.append({
            "path": path,
            "language": raw.get("language") or meta.language,
            "role": raw.get("role") or meta.role,
            "context_role": raw.get("context_role") if raw.get("context_role") in {"implementation", "verification"} else "implementation",
            "access": raw.get("access") if raw.get("access") in {"read_write", "read_only"} else ("read_only" if path.casefold().endswith((".md", ".txt")) else "read_write"),
        })
    repo_data["relevant_files"] = safe_relevant
    architecture = [str(x).strip() for x in (repo_data.get("architecture_context") or []) if str(x).strip()]
    if bootstrap and not any("bootstrap" in x.casefold() or "greenfield" in x.casefold() for x in architecture):
        architecture.insert(0, "bootstrap_project")
    repo_data["architecture_context"] = architecture
    evidence = [str(x).strip() for x in (repo_data.get("analysis_evidence") or []) if str(x).strip()]
    evidence.extend([f"snapshot_file_count={len(snapshot.files)}", f"bootstrap_project={str(bootstrap).lower()}", "analysis_authority=kb"])
    repo_data["analysis_evidence"] = list(dict.fromkeys(evidence))

    try:
        req = RequirementAnalysisInput.model_validate(req_data)
        repo = RepositoryAnalysisInput.model_validate(repo_data)
    except Exception as exc:
        raise GovernedAnalysisError(f"Governed analysis output failed schema validation: {exc}") from exc
    diagnostics = {"model": model, "bootstrap_project": bootstrap, "approved_knowledge_count": len(knowledge)}
    return req, repo, diagnostics
