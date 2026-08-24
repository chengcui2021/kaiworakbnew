# Ticket Summaries — Short Description + Acceptance Criteria

Condensed version of each phase, sized for pasting straight into a JIRA ticket. Full detail (file paths, code snippets, exact steps) lives in the matching `phase-N-*.md` file linked from [00-index.md](00-index.md).

---

## EPIC — Align metamorphic-kb frontend with sibling repo conventions

**Description:** metamorphic-kb's frontend diverged from three sibling repos (novo-mcp, document-generator-ui, novo_review_tool) that share an identical Vue 3 + Tailwind v4 + shadcn-vue + Pinia + tested-API-layer + Claude Code tooling stack. Bring it into alignment via a phased refactor, no rewrite.

**Acceptance Criteria:**
- All 10 phases below are complete
- `npm run verify` passes (typecheck + lint + unit tests)
- `.claude/skills/frontend/` and `.claude/hooks/` match the sibling repos

---

## Story 1 — Phase 0: Baseline safety net

**Description:** Manually verify and document the current working behavior of all 6 routes before any refactor work starts, since there's no automated test coverage yet.

**Acceptance Criteria:**
- All 6 routes click-through tested and passing
- Workspace CRUD, document lifecycle, search, and context package creation confirmed working
- Baseline notes/screenshots saved for later comparison

---

## Story 2 — Phase 1: Tooling foundation

**Description:** Add ESLint flat config, Prettier, split tsconfig, and standard npm scripts (`lint`, `format`, `typecheck`, `verify`) to match the sibling repos. Config-only, no behavior change.

**Acceptance Criteria:**
- `npm run typecheck` and `npm run lint:check` run clean
- `docker compose up` behaves identically to the Phase 0 baseline

---

## Story 3 — Phase 2: Tailwind v4 + shadcn-vue scaffolding

**Description:** Install Tailwind CSS v4 and shadcn-vue plumbing (`components.json`, `cn()` utility, initial primitives) additively, alongside the existing hand-written CSS.

**Acceptance Criteria:**
- Existing UI renders pixel-identical to baseline
- `npm run build` succeeds with the new Tailwind plugin

---

## Story 4 — Phase 3: Design tokens / theme migration

**Description:** Port design tokens from `style.css` into the shadcn semantic-colors/theme structure and wire up dark mode, preserving the app's existing brand/status colors.

**Acceptance Criteria:**
- Toggling `.dark` on `<html>` resolves the new token variables correctly
- `npm run build` succeeds; old UI still visually unaffected

---

## Story 5 — Phase 4: Layout migration

**Description:** Replace the flat `App.vue`/`AppHeader` shell with a `DefaultLayout` + shadcn Sidebar + route-driven breadcrumbs, matching the sibling repos' shell pattern.

**Acceptance Criteria:**
- Sidebar nav and breadcrumbs work correctly on all 6 routes
- Workspace indicator still visible; dark-mode toggle now visibly affects the whole shell

---

## Story 6 — Phase 5: State management — Pinia

**Description:** Convert the `useWorkspace.ts` singleton composable into a Pinia setup store, with a thin composable wrapper so existing call sites don't change.

**Acceptance Criteria:**
- Workspace list loads on start; active-workspace selection persists across a full reload
- All consumer pages still reflect state correctly

---

## Story 7 — Phase 6: API/service layer

**Description:** Replace the flat `api/index.ts` with a fetch-based `useAPI.ts` + per-domain `useXxxService.ts` files; delete dead template mock code (inventory/customer functions).

**Acceptance Criteria:**
- `npm run typecheck` passes
- Every network-backed feature (workspace, document, search, package CRUD) verified working against the real backend

---

## Story 8 — Phase 7: Component-by-component shadcn-vue migration

**Description:** Incrementally replace hand-rolled components with shadcn-vue primitives, one component at a time; retire `style.css` once nothing references it.

**Acceptance Criteria:**
- Each migrated component visually matches (or intentionally improves on) the baseline
- `style.css` fully removed by the end

---

## Story 9 — Phase 8: Testing infrastructure

**Description:** Add Vitest + Playwright and write initial tests for the Pinia store and API services introduced in Phases 5–6, establishing P0/P1/P2 coverage tiers.

**Acceptance Criteria:**
- `npm run test:unit`, `npm run test:coverage`, `npm run test:e2e` all pass
- `verify` script now includes `test:unit`

---

## Story 10 — Phase 9: Claude Code tooling

**Description:** Install `.claude/skills/frontend/`, hooks, commands, and `CLAUDE.md` copied from the most complete sibling repo; delete the superseded legacy guidance docs.

**Acceptance Criteria:**
- Fresh session: `SessionStart` hook fires cleanly; P0-file edits trigger confirmation; stop is blocked without a verify run
- `FRONTEND_STRUCTURE.md`/`BACKEND_STRUCTURE.md` deleted after confirming no unique content is lost

---

## TICKET — UX review remediation: close the seams between Workspaces and Entries

**Description:** Following the Entries-feature merge (Submit/Browse/Tags/Edit, semantic search, Jira links) landing alongside the original workspace-scoped document workflow, a full UX review — five parallel audits grounded against Reka UI's and Tailwind v4's current documentation — found 2 P0, 21 P1, and 18 P2 findings, six of them cross-cutting root causes rather than one-off bugs. Full detail and file-level implementation guidance lives in `phase-10-ux-critical-fixes.md` through `phase-12-ux-polish.md`.

**Scope:**

*Phase 10 — Critical fixes (P0 + cross-cutting foundations)*
- Fix `FilterBar.vue`'s missing Select/Label accessibility pairing (P0)
- Stop `EntryCard.vue` overfetching in list contexts — add a `readonly` mode (P0)
- Distinguish workspace docs vs. resolved Entries in Approved Knowledge / Context Packages
- Reconcile the three divergent "scope to a workspace" UI patterns (header switcher, WorkspaceDetail's own search, Browse's independent dropdown)

*Phase 11 — Consistency & trust*
- Replace native `confirm()` with one shared confirm dialog (4 call sites: delete workspace, delete/move document, delete tag)
- Fix `WorkspaceDetailPage.vue`'s silent `addDocument` error swallow
- Add unsaved-changes guards to Submit/Edit Entry; add a post-submit "View entry →" link
- Fix Search's half-implemented ARIA tabs, query-loss-on-scope-switch, and missing loading state
- Shell/nav legibility: sidebar group label, active-state matching for entry routes, ThemeSwitcher/WorkspaceIndicator accessibility

*Phase 12 — Polish*
- Emoji → lucide icon consistency (Approved Knowledge, Context Packages, Medical Device PoC)
- Extract a shared Write/Preview markdown tab component (currently duplicated on Submit + Edit)
- Extend `MarkdownContent.vue` styling to blockquote/table/img
- Reorganize `EditEntryPage.vue`'s form into sub-sections; group the Status select
- `TagsPanel`/`JiraLinksPanel` → the app's `Alert` pattern
- Context Packages entry-picker filter, hash-copy `aria-live`, similarity-score tooltip, PoC step connector

**Acceptance Criteria:**
- [ ] All three phases complete; checked off in `docs/tasks/00-index.md`
- [ ] `npm run verify` passes
- [ ] No native `confirm()` remains anywhere for a destructive action
- [ ] `FilterBar` announces labels correctly under a screen reader; `EntryCard` fires zero per-row network requests in list view (both manually verified)
- [ ] Workspace scope selection behaves identically across the header switcher, Browse, and Search
- [ ] Workspace-doc vs. resolved-Entry rows are visually distinguishable everywhere they're blended
- [ ] Submit/Edit Entry block navigation away while dirty
- [ ] Search's scope toggle preserves the typed query and shows a loading state
- [ ] `UNTESTED.md` reflects the actual coverage state after this work lands

**Out of scope:** the mixed-ID-selection Context Packages backend limitation (transparent request-split) — tracked separately, not part of this ticket.

---

## EPIC — Editor, templates & search discoverability

**Description:** Three independent net-new feature requests (not part of the UX review remediation arc above): a proper split-view Markdown editor with Mermaid diagram support, a type-first document creation flow with structured templates and a new "Active Workstream" scoping concept, and search/display improvements (section-level result context, a dedicated Agent Retrospective view). Full detail lives in `phase-13-split-view-editor-mermaid.md` through `phase-15-search-sections-agent-retrospective.md`.

**Note:** Phase 14 has two open design decisions (which domain "Document Type" templates attach to; whether "Active Workstream" is a real backend-enforced scope or a client-side filter preset) and Phase 15 has one (whether section-level search is true per-section retrieval or a cheaper post-hoc heading lookup) — see each phase file's "Design decisions to confirm before starting" section. Resolve these before estimating or starting implementation.

---

## Story 11 — Phase 13: Split-view editor & Mermaid rendering

**Description:** Replace the current Write/Preview tab toggle (`MarkdownEditorTabs.vue`) with a VS Code-style side-by-side split view — raw Markdown editor on the left, live-rendered preview on the right — on both Submit and Edit Entry pages. Add `mermaid` as a new dependency and render fenced `​```mermaid` code blocks in the preview as diagrams.

**Acceptance Criteria:**
- Split view (not tabs) shows editor + live preview simultaneously on desktop widths; collapses to a usable toggle on mobile
- A valid `​```mermaid` block renders as an SVG diagram in the preview; an invalid one shows a scoped inline error, not a broken page
- Mermaid-source sanitization doesn't reintroduce an XSS vector (verified with a payload-bearing diagram)
- `npm run verify` passes

---

## Story 12 — Phase 14: Document creation templates & Active Workstream selector

**Description:** Gate "Add Entry" behind a Document Type selection (Tech Spec, Meeting, Review, Background Reference). Structured types render a tabbed/accordion form matching mandatory template headings and auto-generate compliant Markdown; Background Reference keeps a simple drag-and-drop uploader with no forced structure. Add a global "Active Workstream" dropdown in the top nav to scope subsequent actions and searches.

**Acceptance Criteria:**
- Both open design decisions (domain choice; real scope vs. client filter) confirmed in writing before work starts
- Selecting each Document Type renders the correct form; submitting a structured type produces Markdown with exactly the expected headings
- Background Reference accepts a dragged `.md` file
- Active Workstream selector persists across reload and visibly affects at least one downstream action per the resolved design
- Backend migration applies cleanly against an existing populated DB
- `npm run verify` passes

---

## Story 13 — Phase 15: Section-level search results & Agent Retrospective view

**Description:** Show `section_heading`/`heading_path` alongside search result snippets so readers know which part of a long entry matched. Add a new `agent_retrospective` entry type with `confidence`/`lessons_learned` fields, and a dedicated read-only view for reviewers to read an agent's self-assessment alongside its generated output.

**Acceptance Criteria:**
- Section-level approach (true per-section retrieval vs. post-hoc heading lookup) confirmed with ticket owner before implementation
- Search results for a multi-heading entry display the correct section heading/path for the matched text
- `agent_retrospective` entries render a dedicated read-only view with confidence score and lessons learned visible alongside content; no edit controls present
- Backend migration applies cleanly against an existing populated DB
- `npm run verify` passes
