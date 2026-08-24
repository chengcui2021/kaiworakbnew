---
name: e2e-playwright
description: |
  WHEN: writing or editing Playwright end-to-end tests under `e2e/` (`*.spec.ts`),
  the Playwright config, e2e fixtures/mocks; OR adding a user-facing critical
  journey that spans routes + async/polling + teleported UI; OR deciding whether
  something belongs in e2e vs the Vitest unit suite.
  WHEN NOT: pure logic, payload shaping, validators, single-component rendering —
  those stay in Vitest unit tests (`src/**/*.test.ts`).
---

# E2E (Playwright) — metamorphic-kb

End-to-end is a **thin top layer of critical journeys** in a real browser. The
Vitest unit suite owns logic and single-component behaviour. E2E exists to cover
what unit tests structurally cannot: real routing, async data loading, and
**teleported reka-ui overlays** (Dialog / Sheet / Popover / DropdownMenu) that
jsdom can't render — so the unit suite stubs them.

This app has no auth — every route is public. There's no `TEST_PLAN.md` yet;
`e2e/smoke.spec.ts` is currently the only suite (all 6 routes, heading-level
assertions). Add new journeys as their own `*.spec.ts` file under `e2e/`.

## Run
- `npm run test:e2e` — headless (CI-style).
- `npm run test:e2e:ui` — interactive UI **watch** (re-runs on save). UI mode *is* the watch.
- `npx playwright test <file>` / `-g "<title>"` — narrow a run.
- Don't start the dev server yourself — `playwright.config.ts` `webServer` boots
  `npm run dev` on **:5173** and reuses a running one.
- First-time setup: `npx playwright install --with-deps chromium`.

## Separation (do not break this)
- Vitest collects `src/**/*.{test,spec}.{ts,js}`; unit tests are `*.test.ts`.
- E2E is `*.spec.ts` under `e2e/`. **Never put e2e under `src/`** and never name a
  unit test `.spec.ts` — that's the only thing keeping the two runners apart.
- Keep CI e2e a separate job from unit tests + build.

## Mocked-first (the default)
Every test intercepts the backend at the network boundary so it's deterministic
and needs no running backend. Use `mockApi` from `e2e/support/mockApi.ts`:

```ts
import { test, expect } from '@playwright/test'
import { mockApi, json, DEFAULT_WORKSPACE } from './support/mockApi'

test.beforeEach(async ({ page }) => {
  await mockApi(page)
})

test('creating a workspace', async ({ page }) => {
  await page.route('**/api/workspaces', (route) => {
    if (route.request().method() === 'POST') {
      return route.fulfill(json({ ...DEFAULT_WORKSPACE, id: 'ws-new', name: 'New WS' }))
    }
    return route.fulfill(json([DEFAULT_WORKSPACE]))
  })
  // …drive the UI, then assert on the resulting page state.
})
```

`mockApi(page)` takes no overrides argument — it's a flat set of defaults for
every KB endpoint. To override one for a specific test, register your own
`page.route()` call for that path **after** calling `mockApi(page)` (Playwright
matches the most-recently-registered route first, so yours wins).

### Hard-won mocking rules
1. **Route order**: Playwright matches the *most-recently-registered* route first.
   Call `mockApi(page)` first, then add test-specific overrides after — the
   specifics win.
2. **Match on the path with regex/glob, not the origin.** The dev server issues
   relative `/api/...` requests (`VITE_API_BASE_URL` is unset locally), so anchor
   matchers on `**/api/...`.
3. **Assert the contract, not just the UI.** Capture request bodies
   (`route.request().postDataJSON()`) and assert the shape the backend expects
   for create/update/delete journeys.
4. **Faithful fixtures.** Keep every required field populated; a thin mock that
   omits a field the render reads unguarded crashes the page (a real failure
   mode — catch it in a test, don't ship it in a fixture).

## Selectors & assertions
- Prefer `data-test="..."` attributes (this app's existing convention — see
  components/pages for examples) via `page.locator('[data-test="..."]')`, or
  `getByRole`/`getByText` for headings and buttons. Where a page lacks a
  `data-test` hook, add one in the same change rather than coupling to brittle
  CSS.
- Playwright **auto-waits**; use `expect(locator).toBeVisible()` and
  `expect.poll()` for captured state. No manual sleeps.
- For teleported overlays (Dialog, DropdownMenu), just assert the content — it
  renders into `<body>` but is still in the page, so locators find it.

## What to cover (and not)
- **Cover**: the 6-route smoke suite (already done), plus feature journeys as
  they're added — workspace CRUD, document lifecycle (create/approve/move/delete),
  search, context package creation. One happy path + the key error branch per
  journey.
- **Don't cover**: exhaustive form permutations (one happy + one error per
  form), or logic a unit test already pins.
