# Phase 12 — UX Review: Polish

**Depends on:** Phase 10, Phase 11
**Blocks:** none — this is the tail of the UX review remediation arc
**Risk:** low — cosmetic and small-scope functional additions, no shared/foundational files touched

## Origin

Final phase of the post-merge UX review remediation (see `phase-10-ux-critical-fixes.md` for the review's full context and methodology). These are the P2 findings — real, but lower-stakes than Phases 10-11. Each item is independent; work through them in any order, one PR/commit per item recommended (mirrors Phase 7's per-component approach) since there's no dependency chain within this phase.

## Goal

Close out the remaining polish findings: icon-language consistency, shared component extraction, markdown rendering completeness, form organization, and a few small scaling/discoverability gaps.

## Work items

### 1. Icon-language consistency

**Files:** `frontend/src/pages/ApprovedKnowledgePage.vue`, `frontend/src/pages/ContextPackagesPage.vue`, `frontend/src/pages/MedicalDevicePocPage.vue`
**Skills to apply:** `shadcn-vue`, `tailwind`

Replace the raw emoji page-icons (📗, 📦, 🩺) with `lucide-vue-next` icons, matching the convention already established in `AppSidebar.vue` and every button/badge in the app. Suggested mappings: `BookCheck` or `BadgeCheck` for Approved Knowledge (already used in the sidebar — reuse it for visual continuity), `PackageCheck` for Context Packages (also already used in the sidebar), `Stethoscope` for Medical Device PoC (also already in the sidebar).

### 2. Shared Write/Preview tab component

**Files:** `frontend/src/pages/SubmitEntryPage.vue`, `frontend/src/pages/EditEntryPage.vue`
**New file (suggested):** `frontend/src/components/MarkdownEditorTabs.vue`
**Skills to apply:** `shadcn-vue`, `vue3-typescript`

The ~15-line Write/Preview toggle is duplicated verbatim across both pages, each copy with incomplete ARIA tab wiring (`role="tab"`/`aria-selected` without `aria-controls` or `role="tabpanel"`). Extract one shared component (`v-model` for the active mode, default slot or named slots for the write/preview content) and wire it correctly once — Reka UI's `Tabs` primitive is the natural fit if it's added in Phase 11 for the Search scope toggle; reuse it here rather than hand-rolling ARIA a third time.

### 3. `MarkdownContent.vue` styling completeness

**File:** `frontend/src/components/MarkdownContent.vue`
**Skills to apply:** `tailwind`

Current Tailwind arbitrary-selector styling covers `h1`-`h3`, `p`, `ul`/`ol`/`li`, `code`, `pre`, and `a`, but not `blockquote`, `table`, or `img`. Since `SubmitEntryPage.vue` explicitly invites pasting arbitrary Markdown (meeting notes, etc.), unstyled tables or oversized images will render broken in the one place this app most needs faithful content rendering. Extend the arbitrary-selector list to cover these three, following the same pattern already used for the existing elements (see the component for the exact class-list convention).

### 4. `EditEntryPage.vue` form organization

**File:** `frontend/src/pages/EditEntryPage.vue`
**Skills to apply:** `shadcn-vue`, `tailwind`

- The right column stacks 6 form fields, `JiraLinksPanel`, `TagsPanel`, an alert, and 3 buttons under a single "Specifications" heading with no internal separation — entries with several tags or Jira links produce a visually lopsided page next to the fixed-height editor column. Break the right column into labeled sub-sections (e.g. "Classification", "Links & Tags", "Actions"), each its own `Card` or a `<Separator>`-divided block within the existing card.
- The Status `<Select>` is currently a flat 9-value list mixing lifecycle statuses (`open`/`resolved`/`deferred`/`superseded`) with unrelated publish-style ones (`draft`/`pending_review`/`published`/`archived`/`rejected`). Group them with `SelectGroup`/`SelectLabel` so the two families are visually distinct.
- The destructive "Delete" button currently sits directly across from "Cancel"/"Save Changes" in the same row, risking a misclick on narrow viewports. Give it more visual separation — its own row above the Cancel/Save row, or additional gap plus a visually distinct placement (e.g. left-aligned while Cancel/Save stay right-aligned, which is already the layout — just increase the gap and consider a visual divider between them).

### 5. Message/error pattern consistency

**Files:** `frontend/src/components/TagsPanel.vue`, `frontend/src/components/JiraLinksPanel.vue`
**Skills to apply:** `shadcn-vue`

Both currently render bespoke inline `<p>` tags for success/error messages instead of the `Alert`/`AlertDescription` pattern used everywhere else in the app (Submit, Edit, Browse, Search, Tags admin all use it). Switch both panels to match.

### 6. Small scaling/discoverability gaps

**Skills to apply:** `shadcn-vue`, `api-service-layer`

- `frontend/src/pages/ContextPackagesPage.vue` — add a text filter input above the entry picker; it currently has no way to narrow the list and won't scale past ~15-20 approved items.
- `frontend/src/pages/ContextPackagesPage.vue` — packages are approved-by-construction (only pre-approved source material is selectable) but nothing in the UI says so, which can read as if a hidden manual-review step exists. Add a short explanatory line near "Export Context Lock."
- `frontend/src/components/ContextHash.vue` — the copy-hash "Copied!" confirmation has no `aria-live` region; wrap it in `aria-live="polite"` so screen readers announce the confirmation.
- `frontend/src/components/EntryCard.vue` / wherever the similarity badge renders — the "% match" badge has no explanation of what it means to a non-ML-literate user. Add a `Tooltip` (already used elsewhere, e.g. `ContextHash.vue`) explaining it's a semantic-similarity score.
- `frontend/src/pages/MedicalDevicePocPage.vue` — add a thin visual connector between the five numbered step cards to reinforce that they're one sequential flow, not five independent cards. This page is otherwise the best-organized in the app (explicit step state, clear blocked/unblocked messaging) — the Submit/Edit Entry pages could eventually borrow this step-based pattern, but that's out of scope for this phase.

## Files touched

**New (suggested, optional depending on chosen approach):**
- `frontend/src/components/MarkdownEditorTabs.vue`

**Modified:**
- `frontend/src/pages/ApprovedKnowledgePage.vue`
- `frontend/src/pages/ContextPackagesPage.vue`
- `frontend/src/pages/MedicalDevicePocPage.vue`
- `frontend/src/pages/SubmitEntryPage.vue`
- `frontend/src/pages/EditEntryPage.vue`
- `frontend/src/components/MarkdownContent.vue`
- `frontend/src/components/TagsPanel.vue`
- `frontend/src/components/JiraLinksPanel.vue`
- `frontend/src/components/ContextHash.vue`
- `frontend/src/components/EntryCard.vue`

## Verification / Definition of Done

- [ ] `npx vue-tsc --noEmit` passes
- [ ] `npx eslint .` passes
- [ ] Visual check: all three emoji page-icons replaced, visually consistent with sidebar icons
- [ ] Visual check: Write/Preview toggle behaves identically on Submit and Edit after extraction into a shared component; keyboard arrow-key navigation works if built on `Tabs`
- [ ] Manual check: paste Markdown containing a table, a blockquote, and an image into Submit's preview — all render with reasonable styling, no overflow/breakage
- [ ] Visual check: `EditEntryPage.vue`'s right column reads as distinct sub-sections; Status select shows grouped options; Delete is visually separated from Cancel/Save
- [ ] Visual check: `TagsPanel`/`JiraLinksPanel` messages render as `Alert` components, matching the rest of the app
- [ ] Manual check: Context Packages entry picker is filterable; explanatory copy present near Export Context Lock
- [ ] Manual accessibility check: copy-hash confirmation is announced by a screen reader; similarity-score tooltip is present and readable
- [ ] `npm run test:unit` passes
- [ ] `npm run test:e2e` passes
- [ ] `UNTESTED.md` updated
- [ ] `npm run verify` passes
- [ ] Update `docs/tasks/00-index.md`: check off Phases 10-12 once all three are merged and verified
