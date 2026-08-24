# Phase 10 — UX Review: Critical Fixes (P0 + Cross-Cutting Foundations)

**Depends on:** Phase 7 (shadcn-vue migration), Phase 9 (Claude Code tooling — the hooks below apply to every edit in this phase), the Entries-feature merge (`types/entry.ts`, `services/useEntryService.ts`, `services/useTagService.ts`, `services/useJiraLinkService.ts`, the `pages/SubmitEntryPage.vue`/`BrowseEntriesPage.vue`/`TagsPage.vue`/`EditEntryPage.vue` quartet)
**Blocks:** Phase 11 (the consistency work assumes source-type distinction and workspace-scope reconciliation from this phase already landed)
**Risk:** low-to-medium — most changes are additive (a new prop, a new sub-heading, a label attribute) rather than architectural; the workspace-scope reconciliation item is the one structural change and should be its own commit

## Origin

This phase (and 11, 12) implements the findings of a full UX review conducted after the Entries-feature merge (Submit/Browse/Tags/Edit + semantic search + Jira links) landed alongside the original workspace-scoped document workflow. The review ran five parallel audits (shell/nav, workspace pages, curation & packaging, search, Entries feature) grounded against Reka UI's own accessibility documentation and Tailwind v4's current responsive patterns (via Context7), then synthesized into 2 P0, 21 P1, and 18 P2 findings, six of which are cross-cutting root causes. This phase fixes the two P0s plus the two highest-leverage cross-cutting items — the ones that, fixed once, close several findings at once.

## Goal

1. Fix the two P0 findings: `FilterBar.vue`'s missing Select/Label accessibility pairing, and `EntryCard.vue`'s overfetching/over-editable rendering in list contexts.
2. Give the blended workspace-doc + resolved-Entry lists in Approved Knowledge and Context Packages a visible source-type distinction, directly de-risking the already-tracked "mixed selection fails with a 404" follow-up.
3. Reconcile the three divergent "scope to a workspace" UI patterns into one.

## Work items

### 1. `frontend/src/components/FilterBar.vue` — Label/SelectTrigger accessibility pairing

**Skills to apply:** `shadcn-vue` (Reka UI component conventions), `vue3-typescript`, `linting`

All five controls (Type, Component, Status, Tag, Limit) currently render a bare `<Label>` with no `for`, next to a `<SelectTrigger>` with no matching `id` — confirmed against Reka UI's own docs, which require either nesting the `SelectRoot` inside the `Label` or pairing `for`/`id` explicitly. A screen reader currently announces five unlabeled comboboxes on every visit to Browse or Search (this component is shared by both).

- Add a stable `id` to each `SelectTrigger` (`type`, `component`, `status`, `tag`, `limit` — scope with a prefix if the component can render more than once on a page) and a matching `for` on each `Label`.
- `SubmitEntryPage.vue` already does this correctly for its own Selects — use it as the reference pattern in this codebase, don't invent a new one.

### 2. `frontend/src/components/EntryCard.vue` — read-only list-context rendering

**Skills to apply:** `shadcn-vue`, `vue3-typescript`, `api-service-layer` (for understanding the panels' fetch behavior), `testing`

`EntryCard` currently renders a fully-editable `JiraLinksPanel` and `TagsPanel` — each firing its own fetch on mount — for every row in Browse and Search results. A 20-result page fires 40+ requests just to paint, and a scannable results list ends up showing full "add a tag" / "link a ticket" input affordances on every row. These two panels were built for `EditEntryPage.vue`'s detail view and reused unmodified inside the list item.

- Add a `readonly?: boolean` prop to `EntryCard.vue` (default `false`, so `EditEntryPage.vue`'s standalone usage — if any — is unaffected; confirm current call sites and set the prop explicitly at each one instead of relying on the default).
- When `readonly` is `true`: render tags and Jira links as static `Badge` lists sourced from `entry.tags` / whatever's already in the `Entry` payload — no `TagsPanel`/`JiraLinksPanel` mount, no fetch, no inputs.
- Update the two call sites (`BrowseEntriesPage.vue`, `SearchPage.vue`'s entries-mode results) to pass `readonly`.
- Note: the `Entry` type does not currently carry Jira links inline (only `tags`) — for the read-only badge row, either extend the list/search API response to include a lightweight Jira-link count/summary, or simply omit the Jira badges in read-only mode and note this as a deliberate scope cut in the PR description. Don't add a new fetch to work around this — that reintroduces the exact problem being fixed.

### 3. Blended-list source-type distinction

**Files:** `frontend/src/pages/ApprovedKnowledgePage.vue`, `frontend/src/pages/ContextPackagesPage.vue`
**Skills to apply:** `shadcn-vue`, `vue3-typescript`, `vue-router` (for the click-through link)

Both pages merge workspace-approved documents with resolved Entries into a single list rendered identically — the reason the known mixed-ID-selection backend limitation is invisible until a user hits submit and gets a 404.

- **`ApprovedKnowledgePage.vue`:** add a small source-type `Badge` ("Workspace doc" / "KB entry") to each row in the blended `entries` list. For Entry-sourced rows, wrap the title in a `RouterLink` to `/entries/:id/edit` (currently Entry-sourced items are a dead end — no way to see full detail, tags, or Jira links from here).
- **`ContextPackagesPage.vue`:** split the entry-picker checkbox list (currently one flat `<ul>`) into two labeled sub-groups — "Workspace documents" and "Resolved KB entries" — using the same source-type signal. This is prep work for the transparent-split fix already discussed for the mixed-selection backend limitation (tracked separately); grouping the picker visually is valuable on its own regardless of when that follow-up lands, since it tells the user *before* they select that these are two different kinds of thing.
- Both pages currently type the blended list as `KbDocument[]`, synthesizing a fake `KbDocument` shape for Entry-sourced items. Add a lightweight discriminant (`source: 'workspace' | 'entry'` field) when constructing these synthetic entries so the template can key off it directly instead of re-deriving it.

### 4. Workspace-scope reconciliation

**Files:** `frontend/src/pages/BrowseEntriesPage.vue`, `frontend/src/pages/WorkspaceDetailPage.vue`
**Skills to apply:** `vue-pinia` (the global active-workspace store), `shadcn-vue`, `vue-router`

Three different UIs currently express "scope to a workspace": the global header switcher (`WorkspaceIndicator.vue`, backed by the Pinia `useWorkspace()` composable and used by every other page), `WorkspaceDetailPage.vue`'s own separate "search within this workspace" widget, and `BrowseEntriesPage.vue`'s fully independent local `<select>` — a direct carryover from the pre-merge standalone prototype, which had no global workspace concept at all.

- `BrowseEntriesPage.vue`: replace the local `selectedWorkspaceId` ref and its `<select>` with the global `useWorkspace()` composable's `activeWorkspace`/`activeWorkspaceId`. The "All KB entries" vs. "this workspace's documents" toggle should key off whether a workspace is active globally, matching the pattern `SearchPage.vue` already established for its own scope toggle post-merge — don't invent a third pattern, reuse that one.
- `WorkspaceDetailPage.vue`: evaluate whether its embedded "search within this workspace" widget can be removed entirely in favor of a link to `/search` (which, scoped to the same active workspace, now does the same thing and more). If removing it outright feels too disruptive for this phase, add a visible link from the widget to `/search` so users discover the fuller feature. Prefer removal if the widget's only remaining unique capability is redundant with `/search`.

## Files touched

**Modified:**
- `frontend/src/components/FilterBar.vue`
- `frontend/src/components/EntryCard.vue`
- `frontend/src/pages/BrowseEntriesPage.vue`
- `frontend/src/pages/SearchPage.vue` (pass `readonly` to `EntryCard`)
- `frontend/src/pages/ApprovedKnowledgePage.vue`
- `frontend/src/pages/ContextPackagesPage.vue`
- `frontend/src/pages/WorkspaceDetailPage.vue`

**Possibly modified (only if the Jira-link read-only badge needs it — see item 2's note):**
- `frontend/src/types/entry.ts`
- `frontend/src/services/useEntryService.ts`
- `backend/app/persistence/schemas.py` / `entries_list_service.py` (only if extending the list/search response — confirm with the user before touching backend contracts, per the Change Protocol's P0-adjacent caution)

## Verification / Definition of Done

- [ ] `npx vue-tsc --noEmit` passes
- [ ] `npx eslint .` passes (or `--fix` for formatting-only issues)
- [ ] Manual accessibility check: tab through `FilterBar`'s five controls with a screen reader (or browser accessibility inspector) and confirm each announces its label
- [ ] Manual network check: open Browse or Search with 10+ results and confirm the network panel shows no per-row Tags/Jira-link fetches
- [ ] Manual click-through: Approved Knowledge and Context Packages both show a clear visual distinction between workspace-doc and KB-entry rows; an Entry-sourced row in Approved Knowledge links to its edit page
- [ ] Manual click-through: Browse Entries' workspace scope now reads from (and updates) the same global active-workspace state as the header switcher and Search
- [ ] `npm run test:unit` passes; add/update tests for any new `EntryCard` prop behavior
- [ ] `npm run test:e2e` passes; extend `e2e/smoke.spec.ts` or add a new `e2e/*.spec.ts` if this phase changes any route's rendered heading or landing state
- [ ] `UNTESTED.md` updated to reflect any newly-covered or newly-added-but-uncovered files
- [ ] `npm run verify` passes (this phase touches shared components reused across multiple pages — treat it as shared infrastructure per the Change Protocol, run the full suite, not just sibling tests)
