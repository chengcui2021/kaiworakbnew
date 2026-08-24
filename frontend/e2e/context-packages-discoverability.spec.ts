import { test, expect } from '@playwright/test'
import { mockApi, json } from './support/mockApi'

/**
 * Covers Phase 12, Story 24: Context Packages entry picker gets a text
 * filter (won't scale past ~15-20 approved items otherwise) and an
 * explanatory line near Export Context Lock clarifying packages are
 * approved-by-construction.
 */
test.describe('Context Packages discoverability', () => {
  test.beforeEach(async ({ page }) => {
    await mockApi(page)
    await page.route('**/api/workspaces/ws-1/documents*', (route) =>
      route.fulfill(
        json([
          {
            id: 'doc-1',
            workspace_id: 'ws-1',
            title: 'Infusion pump API spec',
            content: '...',
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z',
            approval_status: 'approved',
          },
          {
            id: 'doc-2',
            workspace_id: 'ws-1',
            title: 'Retrieval pipeline notes',
            content: '...',
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z',
            approval_status: 'approved',
          },
        ])
      )
    )
  })

  test('filter input narrows the entry picker by title', async ({ page }) => {
    await page.goto('/packages')

    await expect(page.getByText('Infusion pump API spec')).toBeVisible()
    await expect(page.getByText('Retrieval pipeline notes')).toBeVisible()

    await page.locator('[data-test="package-entry-filter"]').fill('infusion')
    await expect(page.getByText('Infusion pump API spec')).toBeVisible()
    await expect(page.getByText('Retrieval pipeline notes')).toBeHidden()

    await page.locator('[data-test="package-entry-filter"]').fill('no-such-entry')
    await expect(page.getByText('No entries match "no-such-entry".')).toBeVisible()
  })

  test('approved-by-construction copy appears near Export Context Lock', async ({ page }) => {
    await page.route('**/api/workspaces/ws-1/packages*', (route) =>
      route.fulfill(
        json([
          {
            id: 'pkg-1',
            workspace_id: 'ws-1',
            name: 'Launch context',
            approval_status: 'approved',
            context_hash: 'sha256:abcdef1234567890',
            selected_entry_ids: ['doc-1'],
            entry_titles: ['Infusion pump API spec'],
            created_at: '2026-01-01T00:00:00Z',
          },
        ])
      )
    )

    await page.goto('/packages')

    await expect(page.getByText(/approved-by-construction/)).toBeVisible()
    await expect(page.getByRole('button', { name: 'Export Context Lock' })).toBeVisible()
  })
})
