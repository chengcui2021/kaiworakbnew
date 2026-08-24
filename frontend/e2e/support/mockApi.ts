import type { Page } from '@playwright/test'

export function json(body: unknown, status = 200) {
  return { status, contentType: 'application/json', body: JSON.stringify(body) }
}

export const DEFAULT_WORKSPACE = {
  id: 'ws-1',
  name: 'Demo Workspace',
  description: 'Seeded for e2e smoke tests',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  document_count: 0,
}

/**
 * Stubs the KB API surface with minimal defaults so the smoke suite can
 * navigate every route without a running backend. Not exhaustive — deeper
 * per-feature E2E scenarios (create/approve/move/delete) can add their own
 * overrides on top of this.
 */
export async function mockApi(page: Page) {
  await page.route('**/api/workspaces', (route) => route.fulfill(json([DEFAULT_WORKSPACE])))
  await page.route('**/api/workspaces/ws-1', (route) => route.fulfill(json(DEFAULT_WORKSPACE)))
  await page.route('**/api/workspaces/*/documents*', (route) => route.fulfill(json([])))
  await page.route('**/api/workspaces/*/activities*', (route) => route.fulfill(json([])))
  await page.route('**/api/workspaces/*/packages*', (route) => route.fulfill(json([])))
  await page.route('**/api/workspaces/*/stats', (route) =>
    route.fulfill(json({ workspace_id: 'ws-1', document_count: 0, total_characters: 0 }))
  )
  await page.route('**/api/workspaces/*/validate', (route) =>
    route.fulfill(
      json({
        workspace_id: 'ws-1',
        workspace_name: DEFAULT_WORKSPACE.name,
        validated_at: '2026-01-01T00:00:00Z',
        overall_status: 'pass',
        checks: [],
      })
    )
  )
  await page.route('**/api/search*', (route) =>
    route.fulfill(json({ query: '', workspace_id: 'ws-1', total: 0, results: [] }))
  )

  // General entries/tags mocks first — specific overrides registered after win
  // (Playwright matches the most-recently-registered route first).
  await page.route('**/api/entries*', (route) =>
    route.fulfill(json({ entries: [], total: 0, limit: 20, offset: 0 }))
  )
  await page.route('**/api/tags*', (route) => route.fulfill(json({ tags: [], count: 0 })))

  await page.route('**/api/entries/search*', (route) =>
    route.fulfill(json({ query: '', results: [], count: 0 }))
  )
  await page.route('**/api/entries/*/tags*', (route) =>
    route.fulfill(json({ entry_id: 'entry-1', tags: [], count: 0 }))
  )
  await page.route('**/api/entries/*/jira-links*', (route) =>
    route.fulfill(json({ entry_id: 'entry-1', links: [], count: 0 }))
  )
  await page.route('**/api/entries/entry-1', (route) =>
    route.fulfill(
      json({
        id: 'entry-1',
        type: 'documentation',
        component: 'api',
        title: 'Demo entry',
        content: 'Seeded for e2e smoke tests',
        source: null,
        author: 'e2e',
        status: 'open',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
        tags: [],
      })
    )
  )
}
