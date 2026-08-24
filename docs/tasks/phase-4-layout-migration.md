# Phase 4 — Layout Migration

**Depends on:** Phase 2 (shadcn primitives), Phase 3 (theme tokens)
**Blocks:** Phase 7 (component migration happens inside this new shell)
**Risk:** medium — first phase with real visible/structural change

## Goal

Replace the current flat `App.vue` + `AppHeader.vue` shell with the shadcn-vue sidebar layout pattern (`DefaultLayout.vue` + `AppSidebar.vue`) used by all 3 sibling repos, including route-driven breadcrumbs and the theme switcher. This is the first phase where the app visibly changes — treat it as its own reviewable, revertable unit, and do a full manual click-through (not just a glance) before moving on.

## Current state

- `frontend/src/App.vue`: simple shell — `<AppHeader />` + error banner + `<main class="app-main"><RouterView /></main>`
- `frontend/src/components/AppHeader.vue`: top nav bar with `RouterLink`s to all 6 routes + `WorkspaceIndicator.vue` showing the active workspace
- `frontend/src/router/index.ts`: 6 routes, no `meta` fields currently

## Reference pattern (adapt from `novo-mcp/frontend/src/layouts/DefaultLayout.vue`)

metamorphic-kb has **no authentication**, so unlike the reference repos there is no `AuthLayout.vue` or `NavUser` dropdown to build — only `DefaultLayout.vue` is needed, and `AppSidebar.vue` should be simplified to a single nav group (no `NavSecondary`/`NavUser`/`NavWorkspaces` complexity from the reference).

### `frontend/src/layouts/DefaultLayout.vue`
Structure (read `novo-mcp/frontend/src/layouts/DefaultLayout.vue` for the exact shadcn composition):
```vue
<template>
  <SidebarProvider>
    <AppSidebar />
    <SidebarInset>
      <header class="flex h-16 items-center gap-2 border-b px-4">
        <SidebarTrigger />
        <Separator orientation="vertical" class="h-4" />
        <Breadcrumb>
          <!-- built from route.meta.breadcrumb -->
        </Breadcrumb>
        <div class="ml-auto flex items-center gap-2">
          <WorkspaceIndicator />
          <ThemeSwitcher />
        </div>
      </header>
      <main class="flex-1 p-6">
        <RouterView />
      </main>
    </SidebarInset>
  </SidebarProvider>
</template>
```
**Do not** copy the reference's "sandbox mode banner" block (`localStorage` clear button) — that's specific to those repos' sandbox/demo-mode feature, not applicable here.

### `frontend/src/components/AppSidebar.vue`
Simplified nav — one `SidebarMenu` with an item per route (Workspaces, Approved Knowledge, Context Packages, Search, Medical Device PoC), each with a `lucide-vue-next` icon and `RouterLink`. No `NavUser`, no auth-gated items.

### `frontend/src/components/ThemeSwitcher.vue`
Copy from any reference repo — a small button/toggle calling `useColorMode()` (already wired in `main.ts` from Phase 3) to flip light/dark.

### Additional shadcn primitives needed
```bash
cd frontend && npx shadcn-vue@latest add sidebar breadcrumb separator sonner
```

### `frontend/src/router/index.ts` changes
Add `meta` to every route:
```typescript
{
  path: '/workspaces',
  component: WorkspacesPage,
  meta: {
    layout: 'DefaultLayout',
    breadcrumb: [{ label: 'Workspaces', to: '/workspaces' }],
  },
}
```
Repeat for all 6 routes with appropriate breadcrumb trails (e.g. `/workspaces/:id` should have a two-level breadcrumb: Workspaces → the workspace name, though the name may need to be resolved dynamically — check how the reference repos handle dynamic breadcrumb segments, e.g. via a route-level `beforeEnter` or a computed in the layout).

### `frontend/src/App.vue` rewrite
```vue
<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import { Toaster } from '@/components/ui/sonner'

const route = useRoute()
const layout = computed(() => DefaultLayout) // only one layout exists — no auth/AuthLayout needed
</script>

<template>
  <component :is="layout">
    <RouterView />
  </component>
  <Toaster />
</template>
```
Since there's no auth, the dynamic-layout-selection logic from the reference repos (`route.meta?.layout === 'AuthLayout' ? AuthLayout : DefaultLayout`) collapses to always `DefaultLayout` — but keep the `meta.layout` field on routes anyway for forward-compatibility/consistency with the reference pattern, even though it's not branched on yet.

### Workspace indicator relocation
`WorkspaceIndicator.vue` currently lives in the old `AppHeader.vue`. Move its usage into `DefaultLayout.vue`'s header (as shown in the template above) — the component itself likely doesn't need internal changes, just a new parent.

## Files touched

**New:**
- `frontend/src/layouts/DefaultLayout.vue`
- `frontend/src/components/AppSidebar.vue`
- `frontend/src/components/ThemeSwitcher.vue`
- `frontend/src/components/ui/{sidebar,breadcrumb,separator,sonner}/*` (shadcn primitives)

**Modified:**
- `frontend/src/App.vue` — full rewrite per above
- `frontend/src/router/index.ts` — add `meta.layout`/`meta.breadcrumb` to all 6 routes

**Deleted:**
- `frontend/src/components/AppHeader.vue` — superseded by `DefaultLayout.vue`'s header + `AppSidebar.vue`

## Dependencies to add

`vue-sonner` (for the `Toaster` component — `reka-ui`/`lucide-vue-next` already added in Phase 2).

## Verification / Definition of Done

- [ ] Full click-through of all 6 routes: sidebar navigation works and highlights the active route
- [ ] Breadcrumbs update correctly per route (including the dynamic workspace-name segment on `/workspaces/:id`)
- [ ] Active workspace indicator still visible and functional in the new header
- [ ] Dark-mode toggle (via `ThemeSwitcher`) now visibly changes the whole shell — this is the first real end-to-end proof that Phase 3's tokens work
- [ ] `npm run typecheck` and `npm run lint:check` pass
- [ ] Re-run the full Phase 0 checklist against the new shell — every feature must still work, just inside the new layout
