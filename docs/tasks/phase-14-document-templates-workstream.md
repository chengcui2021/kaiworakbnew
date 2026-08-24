# Phase 14 — Document Creation Templates & Active Workstream Selector

**Depends on:** none functionally, but touches the same "scoping" territory as Phase 10's item "Reconcile the three divergent scope-to-a-workspace UI patterns" — read that first
**Blocks:** none
**Risk:** high — this is the largest-scope ticket of the three in this batch: it adds a new backend field/migration, introduces a wholly new "workstream" concept alongside the existing "workspace" concept, and has two open design decisions that need product/eng sign-off before implementation starts (see below)

## Origin

New feature request (JIRA), not part of the UX review remediation arc:
- "Update the 'Add Document' flow to require selecting a Document Type from a dropdown first."
- "Structured Types (Tech Spec, Meeting, Review): Render a structured form with tabs or accordions matching the mandatory template headings. Auto-generate the underlying Markdown to ensure perfect heading compliance."
- "Background Reference: Render a simple drag-and-drop file uploader or blank rich-text canvas (no forced structure)."
- "Workstream Selector: Add a global 'Active Workstream' dropdown in the top navigation to scope all subsequent actions and searches."

## Design decisions to confirm before starting

This app has **two parallel, non-overlapping domains** that both look like "documents" from the ticket's description, and the ticket's wording doesn't disambiguate which one it means. Resolve this before writing code:

1. **Which domain do "Document Type" templates attach to?**
   - **Entry domain** (`backend/app/persistence/models.py` `EntryType` enum → `frontend/src/constants/entryOptions.ts` → `SubmitEntryPage.vue`/`EditEntryPage.vue`): the actively-developed KB entry system with tags, Jira links, semantic search, and a `component`/`source`/`status` classification. Not workspace-scoped today.
   - **Document domain** (`backend/app/schemas/models.py` `Document` → `WorkspaceDetailPage.vue`'s "Add document" card, `WorkspaceDetailPage.vue:191-210`): a bare `title` + `content` model, workspace-scoped, used for the Medical Device PoC / Context Packages workflow.
   - **Recommendation:** build this on the **Entry domain**. It's the domain getting active investment (tags, search, review remediation), and the ticket's "Document Type" concept (Tech Spec / Meeting / Review / Background Reference) is a content-shape classification, which is closer to `EntryType`'s existing role than to the Document model's total lack of typing. Building it on the legacy Document model instead would add complexity to a model that's arguably a consolidation candidate, not an expansion candidate (see Phase 10's finding that the two domains already confuse users). Flag this recommendation to whoever owns the ticket and get explicit confirmation — this decision changes which files below apply.

2. **Is "Active Workstream" a new backend-enforced scope, or a client-side saved-filter?**
   - The ticket says the selector should "scope all subsequent actions and searches" — that only holds true end-to-end if entries actually carry a `workstream_id` the backend filters on. Entries aren't scoped to anything today (unlike Documents, which are workspace-scoped).
   - A client-only version (a saved `component`/`tag` filter preset, no backend change) is far cheaper but wouldn't satisfy "scope... searches" in the way the ticket implies — a search would just apply the same optional filters a user could already set by hand in `FilterBar.vue`.
   - **Recommendation:** implement it as a real backend-enforced scope (see item 4 below) if this is meant to be a durable, cross-session concept users rely on; get sign-off before starting since it's the difference between a one-day client change and a migration + API change.

## Work items

### 1. Backend: new classification field for structured templates

**Files:** `backend/app/persistence/models.py`, `backend/app/persistence/schemas.py`, `backend/alembic/` (new migration)

Add a new field — do not overload the existing `EntryType` enum (`documentation`/`requirement`/`constraint`/`example`/`other` answers a different question than "which template was this authored from"). Suggested: `document_template: str | None` on the `Entry` model/table, enum-like at the application layer (`tech_spec`, `meeting`, `review`, `background_reference`), nullable so existing entries are unaffected. Write the Alembic migration accordingly.

### 2. Frontend: type-first "Add Entry" flow

**Files:** `frontend/src/pages/SubmitEntryPage.vue`, `frontend/src/constants/entryOptions.ts` (add a `DOCUMENT_TEMPLATES` list)

Gate the existing single-form flow behind a first step: a `Select` for Document Type (`Tech Spec` / `Meeting` / `Review` / `Background Reference`). The rest of the form renders conditionally based on the choice (item 3/4 below).

### 3. Structured-type forms (Tech Spec, Meeting, Review)

**New files (suggested):** `frontend/src/components/entry-templates/TechSpecForm.vue`, `MeetingForm.vue`, `ReviewForm.vue` (or a single data-driven `StructuredTemplateForm.vue` keyed by a per-template heading list — prefer this if the three templates end up structurally similar, per this app's general preference for one shared component over near-duplicates)

- Get the mandatory heading list per template confirmed by whoever owns the ticket before building — the ticket names the three types but not their required sections. Placeholder suggestion pending confirmation: Tech Spec (`Overview`, `Goals`, `Non-Goals`, `Design`, `Alternatives Considered`, `Rollout Plan`); Meeting (`Attendees`, `Agenda`, `Decisions`, `Action Items`); Review (`Summary`, `Findings`, `Recommendation`).
- Render each heading as a tab or accordion section (reuse shadcn `Tabs`/`Accordion`, matching `MarkdownEditorTabs.vue`'s existing pattern rather than a new interaction style).
- On submit, concatenate each section under its `## Heading` into the single Markdown string the existing `createEntry({ content, ... })` call expects (`frontend/src/services/useEntryService.ts`) — this keeps the backend `content: string` contract unchanged; heading compliance is enforced entirely client-side at generation time, not by the backend.

### 4. Background Reference: drag-and-drop upload

**Files:** `frontend/src/pages/SubmitEntryPage.vue`, `frontend/src/utils/markdownUpload.ts`

`readMarkdownFile`/`onMarkdownFileSelected` already exist and handle file→text loading, currently triggered only by a button-driven `<input type="file">` (`SubmitEntryPage.vue:74-107`). Add `dragover`/`dragleave`/`drop` handlers to the existing write-pane container that call the same `readMarkdownFile` path, so Background Reference gets drag-and-drop for free from the current upload logic — no forced heading structure, matching today's default flow.

### 5. Active Workstream selector

**New files (suggested):** `frontend/src/composables/useWorkstream.ts` (or extend `frontend/src/stores/workspace.ts` — **do not** silently repurpose the existing `useWorkspace`/`WorkspaceIndicator`, since "workspace" already means something narrower and Document-specific; a same-named-but-different-scope concept will reintroduce the exact confusion Phase 10 flagged between Documents and Entries), `frontend/src/components/WorkstreamIndicator.vue` (parallel to `WorkspaceIndicator.vue`, added to `AppSidebar.vue`'s header)

- If item 2 above resolves to "real backend scope": add `workstream_id` to the `Entry` model (migration), filter `search_entries`/`list_entries`/`create_entry` by it, and thread the active workstream through `useEntryService.ts` calls the same way `activeWorkspace.id` threads through `useSearchService.ts` today (`SearchPage.vue:48-60`).
- If client-side-only: store the active workstream as a named `component`/`tag` filter preset in a small Pinia store, applied by default wherever `FilterBar.vue` is used — cheaper, but re-confirm this satisfies the ticket's intent before building it this way.

## Files touched

**New:**
- Backend migration for the new template/workstream field(s)
- `frontend/src/components/entry-templates/*` (structured template forms)
- `frontend/src/composables/useWorkstream.ts` and/or `frontend/src/components/WorkstreamIndicator.vue`

**Modified:**
- `backend/app/persistence/models.py`, `backend/app/persistence/schemas.py`
- `frontend/src/pages/SubmitEntryPage.vue`
- `frontend/src/constants/entryOptions.ts`
- `frontend/src/services/useEntryService.ts`
- `frontend/src/components/AppSidebar.vue`
- `frontend/src/pages/SearchPage.vue` (if workstream scopes search)

## Verification / Definition of Done

- [ ] Design decisions above confirmed in writing (which domain; real scope vs. client filter) before implementation starts
- [ ] `npx vue-tsc --noEmit` passes
- [ ] `npx eslint .` passes
- [ ] Backend migration applies cleanly against an existing populated DB (nullable new column(s), no data loss)
- [ ] Manual check: selecting each Document Type renders the correct form; submitting a structured type produces Markdown with the exact expected headings
- [ ] Manual check: Background Reference accepts a dragged `.md` file the same way the existing upload button does
- [ ] Manual check: Active Workstream selector appears in the top nav, persists across a reload, and visibly affects at least one downstream action (search or entry creation) per the resolved design decision
- [ ] `npm run test:unit` passes (new tests for template-to-Markdown generation and the workstream composable/store)
- [ ] `npm run test:e2e` passes
- [ ] `UNTESTED.md` updated
- [ ] `npm run verify` passes
- [ ] Update `docs/tasks/00-index.md`: check off Phase 14 once merged and verified
