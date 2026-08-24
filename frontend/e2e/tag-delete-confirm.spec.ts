import { test, expect } from '@playwright/test'
import { mockApi, json } from './support/mockApi'

/**
 * Covers the shared confirm-dialog journey (Phase 11, Story 15): deleting a
 * tag now goes through the app's own AlertDialog instead of the browser's
 * native confirm(). Verifies both paths — Cancel leaves the tag in place,
 * Delete removes it — plus the real "used on N entries" count in the copy.
 */
test.describe('Tag delete confirm dialog', () => {
  test.beforeEach(async ({ page }) => {
    await mockApi(page)

    // Bare /api/tags (list) and /api/tags/{id} (delete) are matched
    // separately — Playwright's `*` glob doesn't cross a `/` segment.
    await page.route('**/api/tags', (route) =>
      route.fulfill(json({ tags: [{ id: 'tag-1', name: 'onboarding' }], count: 1 }))
    )
    await page.route('**/api/tags/*', (route) => route.fulfill({ status: 204 }))
    await page.route('**/api/entries?tag=onboarding*', (route) =>
      route.fulfill(json({ entries: [], total: 3, limit: 1, offset: 0 }))
    )
  })

  test('Cancel leaves the tag in place', async ({ page }) => {
    await page.goto('/tags')
    await expect(page.getByText('onboarding')).toBeVisible()

    await page.getByRole('button', { name: 'Delete' }).click()
    await expect(page.getByRole('alertdialog')).toBeVisible()
    await expect(page.getByRole('alertdialog')).toContainText('used on 3 entries')

    await page.getByRole('button', { name: 'Cancel' }).click()
    await expect(page.getByRole('alertdialog')).toBeHidden()
    await expect(page.getByText('onboarding')).toBeVisible()
  })

  test('Delete tag removes it after confirming', async ({ page }) => {
    await page.goto('/tags')
    await page.getByRole('button', { name: 'Delete' }).click()
    await expect(page.getByRole('alertdialog')).toBeVisible()

    // Re-mock the list call to return empty after the delete completes.
    await page.route('**/api/tags', (route) => route.fulfill(json({ tags: [], count: 0 })))

    await page.getByRole('alertdialog').getByRole('button', { name: 'Delete tag' }).click()
    await expect(page.getByText('No tags in the catalog yet.')).toBeVisible()
  })
})
