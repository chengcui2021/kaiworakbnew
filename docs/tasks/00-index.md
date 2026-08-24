# metamorphic-kb Frontend Alignment — Task Index

## Context

metamorphic-kb's frontend was built without knowledge of three sibling repos — `novo-mcp`, `document-generator-ui`, and `novo_review_tool` — which were all built by the same team and independently converged on an identical stack, styling system, and Claude Code tooling setup. As a result, metamorphic-kb is the only one of the four without Tailwind, shadcn-vue, Pinia, ESLint/Prettier, automated tests, or any executable `.claude/` skills/hooks.

This is a **refactor of a working app, not a rewrite** — it must stay deployable at every phase boundary. There is no automated test coverage until Phase 8, so every phase through Phase 7 is verified manually (`docker compose up` + a full click-through of all 6 routes) against the Phase 0 baseline.

Full source roadmap: `~/.claude/plans/ok-we-have-3-velvet-frost.md` (includes reference-repo research notes and JIRA ticket drafts). These task files expand each phase into a comprehensive, standalone spec.

## Reference standard (confirmed identical across novo-mcp, document-generator-ui, novo_review_tool)

Vue 3 Composition API + TypeScript strict + Vite 6, Pinia 2.3, Vue Router 4.5, Tailwind CSS v4 (`@tailwindcss/vite`), shadcn-vue (Reka UI + `class-variance-authority`), fetch-based `useAPI.ts` three-tier service layer, ESLint flat config + Prettier, Vitest + Playwright, and a matching `.claude/skills/frontend/` + `.claude/hooks/` setup with a documented Change Protocol in `CLAUDE.md`.

## How to use these files

Each `phase-N-*.md` file is self-contained: goal, full context, concrete files to create/modify/delete, exact dependencies to add, and a verification checklist. Work through them **in order** — later phases depend on earlier ones (e.g. Phase 6's services are called by Phase 5's Pinia store). Do not skip ahead. Check off each phase below once merged and verified.

## Phase checklist

- [x] [Phase 0 — Baseline safety net](phase-0-baseline-safety-net.md)
- [x] [Phase 1 — Tooling foundation (ESLint, Prettier, tsconfig split)](phase-1-tooling-foundation.md)
- [x] [Phase 2 — Tailwind v4 + shadcn-vue scaffolding](phase-2-tailwind-shadcn-scaffolding.md)
- [x] [Phase 3 — Design tokens / theme migration](phase-3-design-tokens-theme-migration.md)
- [x] [Phase 4 — Layout migration (sidebar shell, breadcrumbs)](phase-4-layout-migration.md)
- [x] [Phase 5 — State management: Pinia](phase-5-pinia-state-management.md)
- [x] [Phase 6 — API/service layer](phase-6-api-service-layer.md)
- [x] [Phase 7 — Component-by-component shadcn-vue migration](phase-7-component-migration.md)
- [x] [Phase 8 — Testing infrastructure](phase-8-testing-infrastructure.md)
- [x] [Phase 9 — Claude Code tooling](phase-9-claude-code-tooling.md)

## UX review remediation (post-merge)

Follow-on initiative after the Entries-feature merge (Submit/Browse/Tags/Edit + semantic
search + Jira links) landed alongside the original workspace-scoped workflow. A full UX
review — five parallel audits grounded against Reka UI's and Tailwind v4's current docs —
found 2 P0, 21 P1, and 18 P2 findings, six of them cross-cutting root causes. These three
phases implement the review's prioritized action plan; same Change Protocol and skill set
as Phases 0-9 apply.

- [x] [Phase 10 — UX review: critical fixes (P0 + cross-cutting foundations)](phase-10-ux-critical-fixes.md)
- [x] [Phase 11 — UX review: consistency & trust](phase-11-ux-consistency-trust.md)
- [x] [Phase 12 — UX review: polish](phase-12-ux-polish.md)

## Editor, templates & search discoverability (net-new features)

Three independent feature requests, unrelated to the UX review remediation above. Phases 14 and 15 each have open design decisions that need product/eng sign-off before implementation — see each phase file's "Design decisions to confirm before starting" section.

- [x] [Phase 13 — Split-view editor & Mermaid rendering](phase-13-split-view-editor-mermaid.md)
- [ ] [Phase 14 — Document creation templates & Active Workstream selector](phase-14-document-templates-workstream.md)
- [ ] [Phase 15 — Section-level search results & Agent Retrospective view](phase-15-search-sections-agent-retrospective.md)

## Reference repo paths (for copying/adapting patterns)

- `/Users/johncarroll/Documents/Repos/novo-mcp` — richest `.claude/` setup, `DefaultLayout.vue`/`AppSidebar.vue` reference
- `/Users/johncarroll/Documents/Repos/document-generator-ui` — second reference, simpler API layer (legacy axios client — do not copy that part)
- `/Users/johncarroll/Documents/Repos/novo_review_tool` — most complete `.claude/skills`+`hooks` copy, richest `useAPI.ts`

## Deferred decisions (resolve when the relevant phase is reached)

- **`eslint-plugin-sonarjs`**: defer past Phase 1, add later if wanted.
- **`vee-validate`/`zod`**: only add in Phase 7 if `WorkspaceForm.vue`'s complexity warrants it.
- **Coverage thresholds (Phase 8)**: start conservative (e.g. global 60%), ratchet up over time.
- **`VITE_API_BASE_URL` naming**: keep metamorphic-kb's existing name (vs. references' `VITE_API_URL`).
