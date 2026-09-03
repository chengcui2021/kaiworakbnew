from app.schemas.context_assembly import GovernedContextFromAnalysisRequest


def test_governed_context_analysis_source_defaults_to_kaiwora():
    payload = GovernedContextFromAnalysisRequest(
        tenant_id="tenant",
        workspace_id="workspace",
        repository_id="repo",
        requirement_analysis={
            "request_id": "KAIWORA-1",
            "title": "Example",
            "description": "Example requirement",
            "acceptance_criteria": [],
        },
        repository_analysis={
            "name": "repo",
            "commit_sha": "abcdef1",
            "relevant_files": [],
        },
    )
    assert payload.analysis_source == "kaiwora"
