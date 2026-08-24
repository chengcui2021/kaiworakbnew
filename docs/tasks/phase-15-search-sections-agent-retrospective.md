# Phase 15 — Section-Level Search Results & Agent Retrospective View

**Depends on:** Phase 14 (reuse its new entry-classification field for the `agent_retrospective` type rather than inventing a second type system — see item 2 below)
**Blocks:** none
**Risk:** high for item 1 (section-level search) — the backend has no chunking/heading-indexing today, so this isn't a display-only change; medium for item 2 (retrospective view) — mostly additive UI plus a few new nullable fields

## Origin

New feature request (JIRA), not part of the UX review remediation arc:
- "Section-Level Results: Update the Search Results UI to display the `section_heading` and `heading_path` alongside the standard title and content snippet."
- "Agent Retrospective View: Create a dedicated, read-only UI view for `agent_retrospective` documents so human reviewers can easily read the agent's self-assessment, confidence scores, and lessons learned alongside the generated outputs."

## Current state

- Semantic search (`GET /api/entries/search`, `backend/app/routes_persistent/semantic_search.py`) embeds and searches **one vector per whole entry** (`semantic_search` in `backend/app/persistence/search_service.py`) — there is no chunking, and no heading parsing, anywhere in the backend today (`grep -rniE "chunk|heading" backend/app` returns nothing).
- `SearchResultItem` (`backend/app/persistence/schemas.py`) wraps a full `EntryResponse` plus a `similarity: float`; there's no `section_heading`/`heading_path` field to surface even if the frontend wanted to display one.
- `frontend/src/components/EntryCard.vue` renders one generic layout for every entry regardless of `entry_type` — no per-type custom view exists.
- No `agent_retrospective` concept — no enum value, no `confidence`/`lessons_learned` fields — exists anywhere in the codebase (`grep -rniE "retrospective|confidence|lessons_learned"` returns nothing in `backend/app` or `frontend/src`).

## Goal

Surface which heading within an entry a search match came from, and give `agent_retrospective` entries their own read-only detail view.

## Work items

### 1. Section-level search results

**Files:** `backend/app/persistence/search_service.py`, `backend/app/persistence/schemas.py`, `backend/app/persistence/models.py` (if chunking), `frontend/src/types/entry.ts`, `frontend/src/components/EntryCard.vue`

This requires a scope decision before implementation, since there's no existing chunking to extend — pick one:

- **(a) True section-level retrieval:** parse each entry's Markdown into sections at ingestion/update time, embed and index each section separately, and return the matched section's heading + its full ancestor path (e.g. `["Design", "Alternatives Considered"]` → `heading_path`) alongside the match. This is the only approach that makes the search *relevance* itself section-aware (a query can match a specific section rather than the whole document), but it's a genuine embeddings/indexing redesign — new table or JSON column for per-section vectors, re-embedding of all existing entries, and query-time aggregation back to one result per entry (or a decision to return multiple section-hits per entry).
- **(b) Post-hoc heading lookup (cheaper):** keep today's one-embedding-per-entry search unchanged, and at result-render time (or in a lightweight backend post-process step) parse the entry's own Markdown to find which heading contains the matched snippet's text, purely for display. Cannot improve retrieval relevance, but satisfies "display the section_heading... alongside the snippet" at a fraction of the cost.
- **Recommendation:** start with (b) — confirm with the ticket owner whether the intent is "help the reader orient within a long entry" (satisfied by (b)) or "make search itself more precise" (requires (a)). Don't build (a) speculatively; it touches the whole ingestion pipeline and every existing entry.
- Whichever is chosen, add `section_heading: str | None` and `heading_path: list[str] | None` to `SearchResultItem`, thread through `frontend/src/types/entry.ts`'s `SearchResultItem`, and render both in `EntryCard.vue` near the existing similarity badge (only in the readonly/list-result context — not on the general entry-detail view where there's no "matched section" to speak of).

### 2. `agent_retrospective` entry type + fields

**Files:** `backend/app/persistence/models.py`, `backend/app/persistence/schemas.py`, `backend/alembic/` (new migration), `frontend/src/constants/entryOptions.ts`

- Reuse Phase 14's new classification field (do not add a second, competing "type of entry" concept) — add `agent_retrospective` as another value there, alongside `tech_spec`/`meeting`/`review`/`background_reference`. If Phase 14 hasn't landed yet, this phase should still design its field to be the same one Phase 14 introduces, not a parallel enum.
- Add the fields the ticket calls out: a `confidence` score (numeric, define range — e.g. `0.0`-`1.0` or `1`-`5`, confirm with ticket owner) and `lessons_learned` (text or a list of short strings) as nullable fields on `Entry`, since these are `agent_retrospective`-specific and meaningless for other entry types.
- These are populated by whatever agent pipeline generates retrospectives (out of scope here — this phase only adds the schema + display surface, not a generation pipeline).

### 3. Read-only Agent Retrospective view

**New file (suggested):** `frontend/src/pages/AgentRetrospectivePage.vue` or `frontend/src/components/AgentRetrospectiveView.vue` (a dedicated read-only layout, not a variant of the editable `EditEntryPage.vue` form — the ticket explicitly asks for a reviewer-facing read view, not an edit form)

- Route it either as a dedicated page (`/entries/:id/retrospective`) or as a conditional render inside the existing entry-detail flow when `entry.document_template === 'agent_retrospective'` — prefer the conditional-render approach if entries are otherwise viewed inline, to avoid a second navigation path to the same data.
- Layout: the retrospective's own self-assessment/confidence/lessons-learned prominently alongside the generated output content (i.e., don't bury the retrospective metadata below the raw Markdown — the ticket's whole point is surfacing it "alongside" the output, not as an afterthought). Render `confidence` as a visible score (number + a simple visual indicator, e.g. a `Badge` or small meter — check the `dataviz` skill if a meter/sparkline component is warranted), and `lessons_learned` as a distinct, clearly-labeled section.
- Read-only: no form controls, no save/submit actions — this view exists purely for human review.

## Files touched

**New:**
- Backend migration for `section_heading`/`heading_path` (if approach (a)) and `confidence`/`lessons_learned`
- `frontend/src/pages/AgentRetrospectivePage.vue` (or equivalent component)

**Modified:**
- `backend/app/persistence/search_service.py`
- `backend/app/persistence/schemas.py`, `backend/app/persistence/models.py`
- `frontend/src/types/entry.ts`
- `frontend/src/components/EntryCard.vue`
- `frontend/src/constants/entryOptions.ts`
- Router config (if a dedicated route is chosen)

## Verification / Definition of Done

- [ ] Section-level approach ((a) vs (b)) confirmed with ticket owner before implementation
- [ ] `npx vue-tsc --noEmit` passes
- [ ] `npx eslint .` passes
- [ ] Backend migration applies cleanly against an existing populated DB
- [ ] Manual check: a search result for an entry with multiple headings shows the correct `section_heading`/`heading_path` for its match
- [ ] Manual check: an `agent_retrospective` entry renders its dedicated read-only view with confidence score and lessons learned visible alongside its content; no edit controls present
- [ ] `npm run test:unit` passes
- [ ] `npm run test:e2e` passes
- [ ] `UNTESTED.md` updated
- [ ] `npm run verify` passes
- [ ] Update `docs/tasks/00-index.md`: check off Phase 15 once merged and verified
