# Kaiwora KB-owned Governed Analysis v5.4.0

## Architecture
Customer/Agent UI -> Agent/Core (collect immutable work-item + repo snapshot facts) -> KB /api/governed-context/analyse-and-lock -> seed approved-knowledge resolution -> Qwen via Kaiwora Model Gateway -> governed requirement/repository analysis -> final approved-knowledge resolution -> Context Assembly -> immutable Context Lock -> Project Run.

## Important behaviour
- KB is the analysis authority for Project Run creation.
- Agent/Core no longer performs the model-based requirement/repository analysis for the create+lock path; it only collects immutable repository evidence.
- Existing /api/governed-context/lock-from-analysis remains for compatibility/debug flows.
- Existing tenant/workspace/repository knowledge scoping remains authoritative.
- Bootstrap/greenfield runs fail closed when no approved/resolved knowledge is available in the authorised scope.
- BGE-M3 remains the embedding/retrieval model; qwen3-coder:30b is used for governed analysis through the same authenticated Model Gateway.

## Environment
Existing .env values are preserved. Added:
- GOVERNED_ANALYSIS_BASE_URL
- GOVERNED_ANALYSIS_API_KEY
- GOVERNED_ANALYSIS_MODEL=qwen3-coder:30b
- GOVERNED_ANALYSIS_TIMEOUT_SECONDS=120
