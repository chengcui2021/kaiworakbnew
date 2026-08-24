import { test, expect } from '@playwright/test'
import { mockApi, json } from './support/mockApi'

/**
 * Covers the Browse Entries delete action: EntryCard's destructive Delete
 * icon button (shown via `allow-delete` on the Browse page's read-only
 * cards) confirms via the shared AlertDialog, fires a DELETE request, and
 * removes the entry from the list in place — matching the delete flow
 * already covered for EditEntryPage.
 */
test.describe('Browse entries: delete', () => {
  test.beforeEach(async ({ page }) => {
    await mockApi(page)
  })

  test('deleting an entry from its card confirms, sends DELETE, and removes it from the list', async ({
    page,
  }) => {
    const baseEntry = {
      type: 'documentation',
      component: 'api',
      content: 'Seeded for e2e smoke tests',
      source: null,
      author: 'e2e',
      status: 'open',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
      tags: [],
    }
    const entry1 = { ...baseEntry, id: 'entry-1', title: 'First entry' }
    const entry2 = { ...baseEntry, id: 'entry-2', title: 'Second entry' }

    await page.route('**/api/entries?*', (route) =>
      route.fulfill(json({ entries: [entry1, entry2], total: 2, limit: 20, offset: 0 }))
    )

    await page.goto('/browse')
    await expect(page.getByText('First entry')).toBeVisible()
    await expect(page.getByText('Second entry')).toBeVisible()

    let deleteMethod = ''
    await page.route('**/api/entries/entry-1', (route) => {
      deleteMethod = route.request().method()
      return route.fulfill({ status: 204 })
    })

    const deleteButtons = page.getByRole('button', { name: 'Delete entry' })
    await expect(deleteButtons).toHaveCount(2)
    await deleteButtons.first().click()

    await expect(page.getByRole('alertdialog')).toBeVisible()
    await page.getByRole('alertdialog').getByRole('button', { name: 'Delete entry' }).click()

    await expect.poll(() => deleteMethod).toBe('DELETE')
    await expect(page.locator('[data-sonner-toast]')).toContainText('Entry deleted.')
    await expect(page.getByText('First entry')).toHaveCount(0)
    await expect(page.getByText('Second entry')).toBeVisible()
  })

  test('a failed delete shows an error toast and keeps the entry in the list', async ({ page }) => {
    const entry1 = {
      id: 'entry-1',
      type: 'documentation',
      component: 'api',
      title: 'First entry',
      content: 'Seeded for e2e smoke tests',
      source: null,
      author: 'e2e',
      status: 'open',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
      tags: [],
    }

    await page.route('**/api/entries?*', (route) =>
      route.fulfill(json({ entries: [entry1], total: 1, limit: 20, offset: 0 }))
    )

    await page.goto('/browse')
    await expect(page.getByText('First entry')).toBeVisible()

    await page.route('**/api/entries/entry-1', (route) =>
      route.fulfill({ status: 500, contentType: 'application/json', body: '{}' })
    )

    await page.getByRole('button', { name: 'Delete entry' }).click()
    await page.getByRole('alertdialog').getByRole('button', { name: 'Delete entry' }).click()

    const toast = page.locator('[data-sonner-toast]')
    await expect(toast).toBeVisible()
    await expect(toast).toHaveAttribute('data-type', 'error')
    await expect(page.getByText('First entry')).toBeVisible()
  })
})
