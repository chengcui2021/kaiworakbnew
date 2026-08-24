# Kaiwora Agent ↔ Governance/KB Integration

## Runtime contract

The two repositories stay independently deployable but form one Kaiwora product.

1. A customer creates a Project Run with a work item and repository. No `context_lock_id` is required.
2. Agent Core performs requirement analysis and immutable-SHA repository analysis using the configured provider (default: local Qwen through Ollama).
3. Agent Core calls KB `POST /api/governed-context/lock-from-analysis`.
4. KB resolves authoritative approved knowledge plus tenant/repository-scoped **validated** learned knowledge, assembles governed context, and returns an immutable Context Lock.
5. Agent Core stores the Lock ID internally, builds the controlled execution package, and executes the graph through the provider-neutral coding executor (default: OpenCode + Qwen).
6. Verification/AC validation produce evidence and commits.
7. When a run finishes, Agent Core publishes a `LearningEvidencePackage` to KB `POST /api/internal/learning/candidates`. Learning publication is fail-soft and never changes a completed engineering result.
8. KB keeps the first observation as `candidate`. Repeated successful high-confidence evidence for the same tenant/repository fingerprint can auto-promote to `validated`. Candidate learning never enters a Context Lock.
9. The next Project Run can automatically freeze validated learning into its new Context Lock.

## Local Mac mini

Start KB first:

```bash
cd kaiwora-kb
docker compose up --build -d
# KB API -> http://localhost:8000
```

Ensure Ollama is running on the Mac host:

```bash
ollama serve
ollama pull qwen3-coder:30b
ollama pull deepseek-r1:14b
```

Start Agent:

```bash
cd kaiwora-agent
docker compose up --build -d
# Dashboard -> http://localhost:5176
# Agent Core -> http://localhost:9010
```

Agent Compose uses `KB_BASE_URL=http://host.docker.internal:8000`, so KB remains an internal product dependency even though the two Compose projects are separate.

## External Project Run API

```json
{
  "ticket_key": "APP-123",
  "ticket_title": "Implement discount",
  "ticket_description": "Apply the approved pricing rule",
  "acceptance_criteria": ["..."],
  "repository": "https://github.com/acme/app",
  "repository_commit_sha": "<sha>",
  "target_branch": "main",
  "tenant_id": "acme",
  "workspace_id": "engineering"
}
```

The public response exposes the Project Run readiness but not the Context Lock ID or execution package. Those remain internal audit/governance state.

## Provider model

Current runtime has no proprietary model dependency. Supported product routes are `auto`, `qwen_local`, and `deepseek_local`. The core has a `ProviderRegistry` extension point so an Anthropic/OpenAI/Bedrock adapter can be added later without changing Context Lock, governance, execution graph, or validation semantics.
