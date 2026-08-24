# Phase 8 — Testing Infrastructure

**Depends on:** Phase 5 (Pinia store), Phase 6 (services) — these are the highest-priority test targets; ideally also after Phase 7 so component tests target final markup
**Blocks:** Phase 9 (several Claude Code hooks assume Vitest exists)
**Risk:** low — purely additive, establishes the safety net that was missing for Phases 0–7

## Goal

Add Vitest + Playwright to match the sibling repos' testing stack, and write initial tests for the highest-value code introduced in Phases 5–7. This is the point where `npm run verify` finally becomes a meaningful automated gate instead of just typecheck+lint.

## Reference pattern (all 3 sibling repos agree)

- **Unit/component tests:** Vitest 2.1.8 (jsdom environment), `@vue/test-utils`, v8 coverage provider
- **E2E tests:** Playwright 1.61
- Sibling `*.test.ts` files alongside the file under test (not a separate `__tests__/` tree)
- `UNTESTED.md` at the frontend root, tracking P0/P1/P2 coverage tiers for anything not yet covered

## Important deviation from the reference repos

The sibling repos enforce **mature, high coverage thresholds** (P0 95%/90%, P1 85%/75%, P2 60%) accumulated over a long time. metamorphic-kb starts this phase at **0% coverage**. Do not copy those thresholds verbatim into `vitest.config.ts` — start conservative (e.g. a global 60% threshold, or no enforced threshold at all initially) and ratchet up over subsequent work, matching the actual coverage this phase achieves rather than an aspirational number that would immediately fail CI.

## Files to create

### `frontend/vitest.config.ts`
jsdom environment, v8 coverage provider, path alias `@/*` matching `tsconfig.app.json`, exclude `src/components/ui/**` from coverage requirements (shadcn primitives, matches reference repos' convention of not holding third-party-pattern code to the same bar).

### `frontend/playwright.config.ts`
Adapt from a reference repo, point the base URL at this app's dev server port (5173 locally / 3000 via docker-compose — check which one is appropriate for how e2e tests will actually be run).

### `frontend/src/test-setup.ts`
jsdom + `@vue/test-utils` global test configuration (global stubs, plugins like Pinia's testing utilities installed globally if needed).

### `frontend/e2e/`
Initial smoke-test specs: navigate to each of the 6 routes, assert the page renders without error and shows expected key content (e.g. the page heading). This is a smoke suite, not exhaustive E2E coverage — deeper E2E scenarios can be added later.

### `frontend/UNTESTED.md`
Seed with every file under `pages/`, `composables/`, `stores/`, `services/`, tiered:
- **P0 (critical path):** `stores/workspace.ts`, `services/useAPI.ts`, `services/useWorkspaceService.ts` — these are the shared foundation everything else depends on
- **P1:** `services/useDocumentService.ts`, `services/usePackageService.ts`, `services/useSearchService.ts`
- **P2:** display-only page/components not yet covered

### Priority test files to actually write in this phase
In order:
1. `frontend/src/services/useAPI.ts` + `useAPI.test.ts` — the shared foundation, test request success/error handling, the hooks (onBefore/onSuccess/onError/onFinally), and error-map behavior
2. `frontend/src/stores/workspace.ts` + `workspace.test.ts` — test `loadWorkspaces`, `setActiveWorkspace` (including the localStorage side effect — this is the one genuine behavioral contract from Phase 5), and the `activeWorkspace` computed
3. `frontend/src/services/useWorkspaceService.ts` + `useWorkspaceService.test.ts`
4. `frontend/src/services/useDocumentService.ts` + `useDocumentService.test.ts`

## package.json changes

**Scripts:**
```json
{
  "test:unit": "vitest run",
  "test:coverage": "vitest run --coverage",
  "test:e2e": "playwright test",
  "test:e2e:ui": "playwright test --ui",
  "verify": "npm run typecheck && npm run lint:check && npm run test:unit"
}
```
Note `verify` now includes `test:unit` — this is the first phase where it does.

**devDependencies to add:** `vitest`, `@vitest/coverage-v8`, `@vue/test-utils`, `jsdom`, `@playwright/test`, `@pinia/testing`

## Files touched

**New:**
- `frontend/vitest.config.ts`
- `frontend/playwright.config.ts`
- `frontend/src/test-setup.ts`
- `frontend/e2e/*.spec.ts` (smoke specs)
- `frontend/UNTESTED.md`
- `frontend/src/services/useAPI.test.ts`
- `frontend/src/stores/workspace.test.ts`
- `frontend/src/services/useWorkspaceService.test.ts`
- `frontend/src/services/useDocumentService.test.ts`

**Modified:**
- `frontend/package.json` — scripts + devDependencies as above

## Verification / Definition of Done

- [ ] `npm run test:unit` passes
- [ ] `npm run test:coverage` produces a coverage report (doesn't need to hit an aspirational threshold, just needs to run and report honestly)
- [ ] `npm run test:e2e` passes against a running dev server (or `docker compose up` stack)
- [ ] `npm run verify` passes end-to-end (typecheck + lint + unit tests)
- [ ] `UNTESTED.md` accurately reflects what's covered vs. not, tiered P0/P1/P2
