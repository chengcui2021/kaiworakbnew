# Phase 0 — Baseline Safety Net

**Depends on:** nothing (first phase)
**Blocks:** all subsequent phases
**Risk:** none — this phase makes no code changes

## Goal

Establish a "known good" reference for the app's current behavior before any refactor work begins. metamorphic-kb has **zero automated test coverage** today (no Vitest, no Playwright, no ESLint) and won't until Phase 8, so every phase through Phase 7 has to be verified by hand against this baseline. Skipping this step means later phases have nothing concrete to diff against when something looks subtly different.

## Current app surface to baseline

metamorphic-kb frontend is a Vue 3 + Vite 5 + Vue Router 4 app. Routes (from `frontend/src/router/index.ts`):

| Route | Page component | Purpose |
|---|---|---|
| `/` | (redirects to `/workspaces`) | — |
| `/workspaces` | `WorkspacesPage.vue` | List/create/delete workspaces |
| `/workspaces/:id` | `WorkspaceDetailPage.vue` | Workspace detail: documents, activity, validation |
| `/approved` | `ApprovedKnowledgePage.vue` | Approved knowledge view |
| `/packages` | `ContextPackagesPage.vue` | Context package list/create |
| `/search` | `SearchPage.vue` | Search across documents |
| `/medical-device-poc` | `MedicalDevicePocPage.vue` | Medical device PoC view |

State is held in `frontend/src/composables/useWorkspace.ts` (module-level singleton refs, `kb.activeWorkspaceId` persisted to `localStorage`). API calls go through `frontend/src/api/index.ts` → `frontend/src/services/apiClient.ts` (`requestJson<T>()`).

## Steps

1. Ensure Docker is running, then bring up the stack from the repo root:
   ```
   docker compose up --build
   ```
   Backend on `http://localhost:8000`, frontend on `http://localhost:3000` (mapped from container port 5173 — see `docker-compose.yml`).

2. Click through and manually verify each of the following. For each, note pass/fail and take a screenshot (store them wherever you keep working notes — not committed to the repo, this is a personal verification aid):
   - **Workspaces list** (`/workspaces`): loads existing workspaces, "create workspace" flow works, delete works.
   - **Workspace detail** (`/workspaces/:id`): navigating from the list works; document list renders; workspace activity panel renders; workspace validation panel renders and shows check results.
   - **Document lifecycle**: create/upload a document, change its status (approve/archive), move it, delete it — via whatever UI `DocumentList.vue`/`WorkspaceForm.vue` expose.
   - **Approved Knowledge** (`/approved`): renders approved documents correctly.
   - **Context Packages** (`/packages`): list renders, create-package flow works.
   - **Search** (`/search`): search returns results scoped to the active workspace via `SearchBar.vue`.
   - **Medical Device PoC** (`/medical-device-poc`): renders without errors.
   - **Active workspace persistence**: switch the active workspace (via `WorkspaceIndicator.vue`/header), reload the page, confirm the same workspace is still active (this exercises the `kb.activeWorkspaceId` localStorage key that Phase 5 will touch).
   - **Header/nav**: confirm `AppHeader.vue` links all navigate correctly and the active workspace indicator is visible.

3. If anything is already broken, decide with the team whether to fix it now (out of scope for this refactor) or explicitly note it as a known-pre-existing issue so later phases don't get blamed for it.

## Files touched

None. This is a manual verification exercise only.

## Verification / Definition of Done

- [ ] `docker compose up --build` succeeds with no errors in either container's logs
- [ ] All 6 routes load without console errors
- [ ] Workspace CRUD, document lifecycle, search, and context package creation all confirmed working
- [ ] Active-workspace localStorage persistence confirmed working across a reload
- [ ] Baseline notes/screenshots saved somewhere you can reference during Phases 1–7
