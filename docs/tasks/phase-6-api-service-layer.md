# Phase 6 — API/Service Layer

**Depends on:** Phase 5 (Pinia store exists and needs to be repointed to the new service)
**Blocks:** Phase 7 (components consume services when migrated), Phase 8 (services are the first thing tested)
**Risk:** HIGH — highest blast-radius phase in the whole roadmap; touches every data-fetching call site in the app

## Goal

Replace the current flat `frontend/src/api/index.ts` + `frontend/src/services/apiClient.ts` with the three-tier pattern shared by all 3 sibling repos: Component → Composable → `useXxxService.ts` → base `useAPI.ts` composable. Delete the dead "inventory/customer" mock code left over from a starter template. This phase requires careful, methodical execution since a mistake here silently breaks data fetching across the whole app — there's no automated test suite yet (Phase 8 comes after this), so `npm run typecheck` plus a full manual click-through against the real backend are the only safety nets.

## Decision already made: fetch-based, not axios-based

All 3 sibling repos use a fetch-based `useAPI.ts` composable as the dominant/current pattern. (`document-generator-ui` has a legacy `src/lib/apiClient.ts` axios instance, but it has zero active importers in `src/services` — it's vestigial, not the team's live convention.) **Use the fetch-based pattern.**

## Current state to replace

- `frontend/src/api/index.ts`: flat file mixing real KB functions (`listWorkspaces`, `getWorkspace`, `createWorkspace`, `updateWorkspace`, `deleteWorkspace`, `listDocuments`, `createDocument`, `deleteDocument`, `moveDocument`, `setDocumentStatus`, `searchDocuments`, `validateWorkspace`, `getWorkspaceStats`, `listActivities`, `listContextPackages`, `createContextPackage`) **plus dead template leftovers** (`getProducts`, `getSuppliers`, `getPurchaseOrders`, `createPurchaseRequest`, `getCustomers`, `createCustomer`, `updateCustomer`, `deleteCustomer`, `getDemandForecast`, `getSupplierAnalytics`) — the dead functions are never called anywhere and should be deleted, not migrated.
- `frontend/src/services/apiClient.ts`: single generic `requestJson<T>(path, options?)` fetch wrapper, reads `import.meta.env.VITE_API_BASE_URL`.
- Vite dev server proxies `/api` and `/health` to the backend via `VITE_PROXY_TARGET` — **do not touch this proxy config**, it's independent of the service-layer refactor.

## Step 1 — Enumerate every call site before touching anything

```bash
cd frontend && grep -rn "from '.*api'" src --include="*.vue" --include="*.ts"
grep -rn "from '.*apiClient'" src --include="*.vue" --include="*.ts"
```
Write down every file that imports from `../api`, `@/api`, or `apiClient` — this is your checklist for Step 4.

## Step 2 — Build `frontend/src/services/useAPI.ts`

Adapt from `novo_review_tool/frontend/src/services/useAPI.ts` (richest version) or `novo-mcp/frontend/src/services/useAPI.ts`, **trimmed** since metamorphic-kb has no authentication:
- **Drop:** 401-retry-refresh logic, `shouldAttemptRefreshOn401`, any `refreshSessionCookies`/session-related imports
- **Keep:** `makeRequest.get/post/put/patch/delete` methods, `loading`/`error`/`responseData` refs, `mocked`/`mockResponse`/`delay` support (harmless to keep unused, matches convention for future test/demo modes), `errorMap`/`customErrorMessage`, `onBefore`/`onSuccess`/`onError`/`onFinally` hooks
- **Keep the existing env var name** `VITE_API_BASE_URL` (do not rename to the reference repos' `VITE_API_URL` — that would require touching `docker-compose.yml`/deployment config, out of scope for this frontend-only refactor)

Rough shape:
```typescript
import { ref } from 'vue'

interface ApiOptions<TResponse> {
  headers?: Record<string, string>
  body?: unknown
  mocked?: boolean
  delay?: number
  mockResponse?: unknown
  errorMap?: Record<number, string>
  customErrorMessage?: string
  transformResponse?: (data: TResponse) => unknown
  onBefore?: () => void
  onSuccess?: (data: TResponse) => TResponse | void
  onError?: (err: Error) => void
  onFinally?: () => void
}

export function useApi<TResponse>() {
  const responseData = ref<TResponse | null>(null)
  const loading = ref(false)
  const error = ref<Error | null>(null)

  async function request(method: string, path: string, options: ApiOptions<TResponse> = {}) {
    // ...fetch against `${import.meta.env.VITE_API_BASE_URL ?? ''}${path}`, JSON parse,
    // handle non-OK via errorMap/customErrorMessage, call onBefore/onSuccess/onError/onFinally hooks
  }

  const makeRequest = {
    get: (path: string, options?: ApiOptions<TResponse>) => request('GET', path, options),
    post: (path: string, options?: ApiOptions<TResponse>) => request('POST', path, options),
    put: (path: string, options?: ApiOptions<TResponse>) => request('PUT', path, options),
    patch: (path: string, options?: ApiOptions<TResponse>) => request('PATCH', path, options),
    delete: (path: string, options?: ApiOptions<TResponse>) => request('DELETE', path, options),
  }

  return { responseData, loading, error, makeRequest }
}
```
Read the actual reference file for the exact fetch/JSON/error-handling logic — don't hand-wave the implementation, copy the real pattern.

## Step 3 — Split into per-domain services

Create these under `frontend/src/services/`, each wrapping `useApi()`:

- **`useWorkspaceService.ts`**: `listWorkspaces`, `getWorkspace`, `createWorkspace`, `updateWorkspace`, `deleteWorkspace`, `getWorkspaceStats`, `validateWorkspace`, `listActivities`
- **`useDocumentService.ts`**: `listDocuments`, `createDocument`, `deleteDocument`, `moveDocument`, `setDocumentStatus`
- **`usePackageService.ts`**: `listContextPackages`, `createContextPackage`
- **`useSearchService.ts`**: `searchDocuments`

Each function should call `useApi<T>().makeRequest.get/post/...()` with the appropriate `/api/...` path (reuse the exact paths currently in `api/index.ts` — this phase changes *structure*, not *endpoints*).

## Step 4 — Repoint every consumer

Using the checklist from Step 1, update every importer to pull from the new per-domain services instead of `../api`. Update `frontend/src/stores/workspace.ts` (from Phase 5) to call `useWorkspaceService().listWorkspaces()` instead of the placeholder `listWorkspaces` import it had.

## Step 5 — Prune dead code

- **Delete** `frontend/src/api/index.ts` entirely (both the migrated KB functions and the dead inventory/customer mock code) once Step 4 confirms nothing imports from it anymore.
- **Delete** `frontend/src/services/apiClient.ts` (superseded by `useAPI.ts`).
- **Prune `frontend/src/types/domain.ts`**: remove dead types (`Product`, `Supplier`, `PurchaseRequest`, `Customer`, `SupplierNote`, `StockMovement`, `DashboardMetric`, `StatusTone` — verify exact list against the live file) while keeping every KB-domain type (`Workspace` through `WorkspaceActivity` and friends).
- **Audit `frontend/src/utils/format.ts`**: keep helpers actually used by KB components (likely `formatDate`/`formatDateTime`/`formatRelativeTime`), prune helpers only used by the now-deleted inventory UI (likely `formatCurrency`, `formatNumber`, `formatPercent`, `statusClass` — verify with `grep` before deleting each one, don't assume).

## Files touched

**New:**
- `frontend/src/services/useAPI.ts`
- `frontend/src/services/useWorkspaceService.ts`
- `frontend/src/services/useDocumentService.ts`
- `frontend/src/services/usePackageService.ts`
- `frontend/src/services/useSearchService.ts`

**Modified:**
- `frontend/src/stores/workspace.ts` (call new service)
- Every page/component enumerated in Step 1
- `frontend/src/types/domain.ts` (prune dead types)
- `frontend/src/utils/format.ts` (prune dead helpers, verify each with grep first)

**Deleted:**
- `frontend/src/api/index.ts`
- `frontend/src/services/apiClient.ts`

## Verification / Definition of Done

- [ ] `npm run typecheck` passes with zero errors (this catches broken import paths, but **not** silently-wrong endpoint URLs — don't rely on typecheck alone)
- [ ] Full manual click-through of **every** network-backed feature against the real backend, with devtools Network tab open to confirm requests actually fire and succeed:
  - Workspace: list, create, update, delete, view stats, view validation results, view activity log
  - Document: list, create/upload, set status (approve/archive), move, delete
  - Search: query returns results scoped to the active workspace
  - Context packages: list, create
- [ ] `grep -rn "from '.*\/api'" frontend/src` returns zero results (confirms nothing still imports the deleted file)
- [ ] `npm run lint:check` passes
- [ ] Re-run the full Phase 0 checklist — this is the highest-risk phase, don't skip verification steps here
