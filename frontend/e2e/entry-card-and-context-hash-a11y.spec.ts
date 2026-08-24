import { test, expect } from '@playwright/test'
import { mockApi, json } from './support/mockApi'

/**
 * Covers Phase 12, Story 24 accessibility items: ContextHash's copy
 * confirmation is announced via aria-live, and EntryCard's similarity badge
 * has a Tooltip explaining what the percentage means.
 */
test.describe('EntryCard and ContextHash accessibility', () => {
  test.beforeEach(async ({ page }) => {
    await mockApi(page)
  })

  test('ContextHash copy button announces "Copied!" via aria-live', async ({ page, context }) => {
    await context.grantPermissions(['clipboard-read', 'clipboard-write'])
    await page.route('**/api/workspaces/ws-1/packages*', (route) =>
      route.fulfill(
        json([
          {
            id: 'pkg-1',
            workspace_id: 'ws-1',
            name: 'Launch context',
            approval_status: 'approved',
            context_hash: 'sha256:abcdef1234567890',
            selected_entry_ids: [],
            entry_titles: [],
            created_at: '2026-01-01T00:00:00Z',
          },
        ])
      )
    )

    await page.goto('/packages')

    const copyButton = page.getByRole('button', { name: 'Copy' })
    await expect(copyButton).toHaveAttribute('aria-live', 'polite')
    await copyButton.click()
    await expect(page.getByRole('button', { name: 'Copied!' })).toBeVisible()
  })

  test('EntryCard similarity badge has a tooltip explaining the score', async ({ page }) => {
    await page.route('**/api/entries/search*', (route) =>
      route.fulfill(
        json({
          query: 'infusion',
          count: 1,
          results: [
            {
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
              similarity: 0.87,
            },
          ],
        })
      )
    )

    await page.goto('/search')
    await page.getByRole('tab', { name: 'All KB entries' }).click()
    await page.locator('[data-test="search-input"]').fill('infusion')
    await page.locator('[data-test="search-submit"]').click()

    const badge = page.getByText('87.0% match')
    await expect(badge).toBeVisible()
    await badge.hover()
    await expect(page.getByText(/Semantic similarity to your search query/)).toBeVisible()
  })
})
