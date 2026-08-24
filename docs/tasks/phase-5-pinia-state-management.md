# Phase 5 — State Management: Pinia

**Depends on:** Phase 1 (tooling), can run independently of Phases 2–4 (styling/layout) since this is purely a state-layer change
**Blocks:** Phase 6 (the new store calls the new service layer)
**Risk:** medium — behavioral contract (localStorage persistence) must survive unchanged

## Goal

Convert `frontend/src/composables/useWorkspace.ts`'s module-level-ref singleton pattern into a proper Pinia setup store, matching the state-management convention shared by all 3 sibling repos. Keep a thin composable wrapper around the store so every existing call site (`useWorkspace()` imported across pages/components) is untouched — this is an internal refactor, not an API change for consumers.

## Current implementation to preserve

`frontend/src/composables/useWorkspace.ts` currently holds, at module scope (outside any function, so it's a true singleton shared by every importer):
- `workspaces` (ref, list of workspaces)
- `activeWorkspaceId` (ref, persisted to `localStorage` under key `kb.activeWorkspaceId`)
- `activeWorkspace` (computed, derived from the above two)
- `loading` (ref)
- `error` (ref)
- `loadWorkspaces()` (method — fetches and populates `workspaces`)
- `setActiveWorkspace(id)` (method — updates `activeWorkspaceId` **and writes to localStorage**)

Read the actual file before starting — the description above is from prior exploration and may drift slightly from the live implementation. The `localStorage` write in `setActiveWorkspace` is the one genuine behavioral contract in this phase: workspace selection must survive a full page reload, exactly as it does today.

## Reference pattern (all 3 sibling repos agree)

Pinia setup-store convention (see `novo-mcp/frontend/src/stores/auth.ts` for the shape, even though that's an auth store — the pattern is what matters, not the domain):
- Function-based `defineStore(id, setup)`, not the options-API store style
- Return **all** state/getters/actions from the setup function — Pinia setup stores require explicit returns, unlike Vuex-style implicit exposure
- Never call `useWorkspaceStore()` at module top-level — only inside `setup()`/composables/component setup, after Pinia is installed

### `frontend/src/stores/workspace.ts`
```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useWorkspaceService } from '@/services/useWorkspaceService' // NOTE: this service doesn't exist until Phase 6 —
                                                                       // in this phase, keep calling the OLD api/index.ts
                                                                       // functions; Phase 6 will swap this import
import type { Workspace } from '@/types/domain'

const ACTIVE_WORKSPACE_KEY = 'kb.activeWorkspaceId'

export const useWorkspaceStore = defineStore('workspace', () => {
  const workspaces = ref<Workspace[]>([])
  const activeWorkspaceId = ref<string | null>(localStorage.getItem(ACTIVE_WORKSPACE_KEY))
  const loading = ref(false)
  const error = ref<string | null>(null)

  const activeWorkspace = computed(() =>
    workspaces.value.find((w) => w.id === activeWorkspaceId.value) ?? null
  )

  async function loadWorkspaces() {
    loading.value = true
    error.value = null
    try {
      workspaces.value = await listWorkspaces() // from api/index.ts in this phase; from useWorkspaceService in Phase 6
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load workspaces'
    } finally {
      loading.value = false
    }
  }

  function setActiveWorkspace(id: string) {
    activeWorkspaceId.value = id
    localStorage.setItem(ACTIVE_WORKSPACE_KEY, id) // preserve this exact behavior
  }

  return { workspaces, activeWorkspaceId, activeWorkspace, loading, error, loadWorkspaces, setActiveWorkspace }
})
```
**Important:** in this phase, the store's `loadWorkspaces()` should keep calling the existing `frontend/src/api/index.ts` functions (`listWorkspaces`, etc.) — do **not** create `useWorkspaceService.ts` yet, that's Phase 6's job. Keep this phase scoped to state management only.

### `frontend/src/composables/useWorkspace.ts` — becomes a thin wrapper
```typescript
import { storeToRefs } from 'pinia'
import { useWorkspaceStore } from '@/stores/workspace'

export function useWorkspace() {
  const store = useWorkspaceStore()
  const { workspaces, activeWorkspaceId, activeWorkspace, loading, error } = storeToRefs(store)
  return {
    workspaces,
    activeWorkspaceId,
    activeWorkspace,
    loading,
    error,
    loadWorkspaces: store.loadWorkspaces,
    setActiveWorkspace: store.setActiveWorkspace,
  }
}
```
This must expose the **exact same shape** the old composable did, so every consumer (`WorkspacesPage.vue`, `WorkspaceDetailPage.vue`, `SearchPage.vue`, `ContextPackagesPage.vue`, `ApprovedKnowledgePage.vue`, `WorkspaceIndicator.vue`, and any others found via `grep -r "useWorkspace" frontend/src`) needs zero changes to their own code.

### `frontend/src/main.ts`
```typescript
import { createPinia } from 'pinia'
// ...
app.use(createPinia())
app.use(router)
```
Install Pinia **before** router (matches reference repos' ordering, though in practice order rarely matters here — do it anyway for consistency).

## Files touched

**New:**
- `frontend/src/stores/workspace.ts`

**Modified:**
- `frontend/src/composables/useWorkspace.ts` — rewritten as thin wrapper (shown above)
- `frontend/src/main.ts` — `app.use(createPinia())`
- `frontend/package.json` — add `pinia`

## Verification / Definition of Done

- [ ] `grep -r "useWorkspace" frontend/src` — confirm every call site still compiles with zero changes needed on the consumer side
- [ ] Workspace list loads correctly on app start
- [ ] Switching the active workspace via the UI, then doing a **full browser reload**, confirms the same workspace is still active (check `localStorage` in devtools for the `kb.activeWorkspaceId` key — same key name, same behavior as before)
- [ ] Every consumer page (`WorkspacesPage`, `WorkspaceDetailPage`, `SearchPage`, `ContextPackagesPage`, `ApprovedKnowledgePage`) still reflects the active workspace correctly
- [ ] `npm run typecheck` and `npm run lint:check` pass
- [ ] Diff `useWorkspace.ts` before/after — confirm the returned shape is unchanged (same keys, same types)
