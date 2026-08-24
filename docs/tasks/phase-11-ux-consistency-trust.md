# Phase 11 — UX Review: Consistency & Trust

**Depends on:** Phase 10 (this phase's search fixes assume the workspace-scope reconciliation already landed; the confirm-dialog work is independent and can proceed in parallel)
**Blocks:** Phase 12 (polish assumes the app's interaction patterns are consistent before cosmetic pass)
**Risk:** low — mostly isolated, same-shape fixes repeated across a handful of call sites; the one new shared component (confirm dialog) should be built once and reviewed carefully since four call sites depend on it

## Origin

Second phase of the post-merge UX review remediation (see `phase-10-ux-critical-fixes.md` for the review's full context and methodology). This phase addresses the "same fix, several call sites" findings — items where the underlying pattern is already right elsewhere in the app, it just hasn't been applied everywhere.

## Goal

1. Replace every native browser `confirm()` used for a destructive action with the app's own shadcn dialog system.
2. Close two real functional gaps found during the review (a silent error swallow, missing unsaved-changes guards).
3. Fix the Search page's half-implemented ARIA tabs, query-loss-on-toggle, and missing loading state.
4. Fix a cluster of shell/navigation legibility gaps (sidebar grouping, active-state matching, header control accessibility).

## Work items

### 1. Shared destructive-action confirm dialog

**New file:** `frontend/src/components/ConfirmDialog.vue` (or a `useConfirm()` composable wrapping a single app-level `AlertDialog` instance — pick whichever fits the existing `WorkspaceForm.vue` dialog pattern more closely; check how that dialog is driven via `v-model:open` before deciding)
**Skills to apply:** `shadcn-vue` (add the `alert-dialog` primitive if not already present — check `frontend/src/components/ui/` first), `vue3-typescript`

- Add the shadcn `alert-dialog` primitive if it isn't already in `frontend/src/components/ui/` (Phase 7 added `dialog`; `alert-dialog` is a distinct Reka UI primitive built for exactly this "confirm before a destructive action" case — don't reuse the plain `Dialog` component, which has different semantics).
- Build one reusable confirm surface parameterized by title, description, and confirm-button label/variant (`destructive` by default).
- Replace all four native `confirm()` call sites:
  - `frontend/src/pages/WorkspacesPage.vue` — `handleDelete` (delete workspace + cascading documents). Given the blast radius, consider requiring the workspace name to be typed into a confirmation input rather than a plain Yes/No — this is the single most destructive action in the app.
  - `frontend/src/pages/WorkspaceDetailPage.vue` — document delete and document move (two separate confirms)
  - `frontend/src/pages/TagsPage.vue` — `deleteTag`. Also fetch and display a real "used on N entries" count in the confirmation copy instead of the current static warning text — this requires either a new lightweight backend count endpoint or reusing `useEntryService().listEntries({ tag })`'s `total` field to compute it client-side before showing the dialog.

### 2. Functional gaps

**Skills to apply:** `vue3-typescript`, `testing`

- `frontend/src/pages/WorkspaceDetailPage.vue` — `addDocument` has no try/catch, unlike every sibling handler in the file; a thrown error is silently swallowed. Wrap it and set `error.value` to match the rest of the page's error-handling convention.
- `frontend/src/pages/SubmitEntryPage.vue` and `frontend/src/pages/EditEntryPage.vue` — add an unsaved-changes guard. Use Vue Router's `onBeforeRouteLeave` (see the `vue-router` skill) plus a `beforeunload` listener for the tab-close/refresh case; gate on a `isDirty` computed comparing current form state to its initial snapshot.
- `frontend/src/pages/SubmitEntryPage.vue` — on successful submission the form currently just resets with no way to see what was created. Show a "View entry →" `RouterLink` to `/entries/:id/edit` using the id returned from `createEntry()`, alongside the existing success message.

### 3. Search page fixes

**File:** `frontend/src/pages/SearchPage.vue`, `frontend/src/components/SearchBar.vue`
**Skills to apply:** `shadcn-vue`, `vue3-typescript`

- The scope toggle's wrapper has `role="tablist"` but the two `Button`s have no `role="tab"` / `aria-selected` / keyboard arrow-key navigation — a half-implemented ARIA pattern is worse for screen readers than none. Either replace the toggle with Reka UI's `Tabs` primitive (add it via `npx shadcn-vue@latest add tabs` if not present) or drop the `tablist`/`tab` roles entirely and use plain buttons with `aria-pressed`.
- Switching scope currently unmounts/remounts `SearchBar` (the two usages sit in different `v-if`/`v-else` template branches), silently clearing the typed query. Lift the `query` ref to a single shared instance so it survives a scope switch — render one `SearchBar` outside the `v-if`/`v-else` split, or pass `query` down as a controlled prop either way.
- Add a `loading` ref around `runSearch()`, matching the `submitting`/spinner convention used on `SubmitEntryPage.vue` — disable the search button and show pending state while a request is in flight.
- `SearchBar.vue`'s default placeholder ("Search documents in this workspace…") is wrong in entries-scope mode. Add a `placeholder` prop (with the current text as its default, to avoid a breaking change for any other consumer) and pass a mode-specific value from `SearchPage.vue`.

### 4. Shell & navigation legibility

**Files:** `frontend/src/components/AppSidebar.vue`, `frontend/src/components/ThemeSwitcher.vue`, `frontend/src/components/WorkspaceIndicator.vue`
**Skills to apply:** `shadcn-vue`, `tailwind`, `vue-router`

- `AppSidebar.vue` — add a `SidebarGroupLabel` ("Workspaces") to the first nav group, matching the second group's "Knowledge Entries" label.
- `AppSidebar.vue` — extend `isActive()` to also match `route.path.startsWith('/entries/')` so "Browse Entries" highlights while a user is on the entry-edit route.
- `ThemeSwitcher.vue` — both dropdown trigger `Button`s hide their text label below the `sm` breakpoint with no fallback; add `aria-label="Theme"` / `aria-label="Appearance"` so they remain accessible icon-only buttons on narrow viewports.
- `WorkspaceIndicator.vue` — move the raw workspace UUID into a `title` attribute or a shadcn `Tooltip` instead of always rendering it inline next to the name; and add the same `hidden sm:inline` responsive treatment `ThemeSwitcher.vue` already uses, so the three header controls behave consistently as the viewport narrows.

## Files touched

**New:**
- `frontend/src/components/ConfirmDialog.vue` (or `frontend/src/composables/useConfirm.ts`, per whichever shape is chosen)
- `frontend/src/components/ui/alert-dialog/*` (shadcn primitive, if not already present)
- `frontend/src/components/ui/tabs/*` (shadcn primitive, only if the Search scope toggle is rebuilt on `Tabs` rather than de-ARIA'd buttons)

**Modified:**
- `frontend/src/pages/WorkspacesPage.vue`
- `frontend/src/pages/WorkspaceDetailPage.vue`
- `frontend/src/pages/TagsPage.vue`
- `frontend/src/pages/SubmitEntryPage.vue`
- `frontend/src/pages/EditEntryPage.vue`
- `frontend/src/pages/SearchPage.vue`
- `frontend/src/components/SearchBar.vue`
- `frontend/src/components/AppSidebar.vue`
- `frontend/src/components/ThemeSwitcher.vue`
- `frontend/src/components/WorkspaceIndicator.vue`

## Verification / Definition of Done

- [ ] `npx vue-tsc --noEmit` passes
- [ ] `npx eslint .` passes
- [ ] Manual click-through: all four destructive actions (delete workspace, delete document, move document, delete tag) show the new shadcn confirm dialog, not the browser's native one
- [ ] Manual check: deliberately trigger `addDocument` failure (e.g. stop the backend mid-request) and confirm the error now surfaces in the UI instead of failing silently
- [ ] Manual check: start editing/submitting an entry, navigate away without saving, confirm a guard intercepts it
- [ ] Manual click-through: Search — switch scope with a query typed in, confirm the query survives; confirm a loading state appears during search; confirm entries-mode shows the correct placeholder
- [ ] Manual check: keyboard-only navigation through the Search scope toggle behaves sensibly (either real tab semantics or plain buttons — not a broken hybrid)
- [ ] Manual check: sidebar shows a "Workspaces" label on the first group; navigating to an entry's edit page keeps "Browse Entries" highlighted
- [ ] `npm run test:unit` passes; add tests for the new confirm dialog component/composable and the unsaved-changes guard logic
- [ ] `npm run test:e2e` passes; add a journey spec (`e2e/*.spec.ts`, not `smoke.spec.ts`) covering at least one destructive-action confirm flow end-to-end
- [ ] `UNTESTED.md` updated
- [ ] `npm run verify` passes
