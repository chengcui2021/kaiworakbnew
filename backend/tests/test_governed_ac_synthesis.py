import json

import pytest

from app.schemas.context_assembly import RawRequirementInput, RepositorySnapshotInput, RepositorySnapshotFileInput
from app.services import governed_analysis_service as service


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _Client:
    def __init__(self, payload, *args, **kwargs):
        self.payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        return _Response(self.payload)


def _snapshot():
    return RepositorySnapshotInput(
        name="todoapp",
        url="https://example.invalid/todoapp.git",
        branch="main",
        commit_sha="abcdef1",
        files=[RepositorySnapshotFileInput(path="src/App.js", language="js", excerpt="function App() {}")],
        evidence=["collector=test"],
    )


def _install_gateway(monkeypatch, model_object):
    payload = {"choices": [{"message": {"content": json.dumps(model_object)}}]}
    monkeypatch.setattr(service, "_gateway_settings", lambda: ("http://model.invalid/v1", "", "qwen-test", 1.0))
    monkeypatch.setattr(service.httpx, "AsyncClient", lambda *a, **kw: _Client(payload))


@pytest.mark.asyncio
async def test_missing_ticket_ac_is_synthesized_by_kb_governed_analysis(monkeypatch):
    _install_gateway(monkeypatch, {
        "requirement_analysis": {
            "title": "Add todo counter",
            "description": "Show the number of todos",
            "acceptance_criteria": [
                "The counter is visible on the main page.",
                "Adding a todo increments the counter by one.",
                "Removing a todo decrements the counter by one.",
            ],
            "clarified_requirement": "Add a dynamic todo count.",
            "constraints": [], "assumptions": [], "ambiguities": [], "dependencies": [],
        },
        "repository_analysis": {
            "relevant_files": [{"path": "src/App.js", "context_role": "implementation", "access": "read_write"}],
            "impacted_components": ["App"], "dependencies": [], "architecture_context": ["existing_application"], "analysis_evidence": [],
        },
    })
    req, _, diagnostics = await service.analyse_with_approved_knowledge(
        RawRequirementInput(title="Add todo counter", description="Show the number of todos", acceptance_criteria=[]),
        _snapshot(),
        [{"entry_id": "kb-1", "title": "React standard", "content": "Keep state observable."}],
    )
    assert len(req.acceptance_criteria) == 3
    assert diagnostics["acceptance_criteria_source"] == "kb_synthesized"
    assert diagnostics["acceptance_criteria_knowledge_entry_ids"] == ["kb-1"]


@pytest.mark.asyncio
async def test_explicit_ticket_ac_remains_authoritative(monkeypatch):
    _install_gateway(monkeypatch, {
        "requirement_analysis": {
            "title": "Add todo counter", "description": "Show count",
            "acceptance_criteria": ["Model tried to replace this"],
            "constraints": [], "assumptions": [], "ambiguities": [], "dependencies": [],
        },
        "repository_analysis": {
            "relevant_files": [{"path": "src/App.js", "context_role": "implementation", "access": "read_write"}],
            "impacted_components": [], "dependencies": [], "architecture_context": [], "analysis_evidence": [],
        },
    })
    req, _, diagnostics = await service.analyse_with_approved_knowledge(
        RawRequirementInput(title="Add todo counter", description="Show count", acceptance_criteria=["Counter updates after add/remove"]),
        _snapshot(),
        [],
    )
    assert req.acceptance_criteria == ["Counter updates after add/remove"]
    assert diagnostics["acceptance_criteria_source"] == "explicit"


@pytest.mark.asyncio
async def test_missing_ticket_ac_fails_closed_when_model_returns_none(monkeypatch):
    _install_gateway(monkeypatch, {
        "requirement_analysis": {
            "title": "Add todo counter", "description": "Show count", "acceptance_criteria": [],
            "constraints": [], "assumptions": [], "ambiguities": [], "dependencies": [],
        },
        "repository_analysis": {
            "relevant_files": [], "impacted_components": [], "dependencies": [], "architecture_context": [], "analysis_evidence": [],
        },
    })
    with pytest.raises(service.GovernedAnalysisError, match="AC_SYNTHESIS_FAILED"):
        await service.analyse_with_approved_knowledge(
            RawRequirementInput(title="Add todo counter", description="Show count", acceptance_criteria=[]),
            _snapshot(),
            [],
        )
