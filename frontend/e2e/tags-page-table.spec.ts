import { test, expect } from '@playwright/test'
import { mockApi, json } from './support/mockApi'

/**
 * Covers the @tanstack/vue-table consistency pass on TagsPage.vue: the tag
 * catalog now renders via useVueTable (headless sorting) through the shadcn
 * Table primitives instead of a plain <ul>, matching the DocumentList
 * conversion and the novo-mcp blueprint's data-grid pattern. Inline
 * rename-in-row editing is preserved.
 */
test.describe('Tags page data table', () => {
  test.beforeEach(async ({ page }) => {
    await mockApi(page)
    await page.route('**/api/tags', (route) =>
      route.fulfill(
        json({
          tags: [
            { id: 'tag-z', name: 'zebra' },
            { id: 'tag-a', name: 'alpha' },
          ],
          count: 2,
        })
      )
    )
  })

  test('renders as a real table with a sortable Name header', async ({ page }) => {
    await page.goto('/tags')

    const table = page.locator('[data-test="tags-list"]')
    await expect(table).toBeVisible()

    const rows = table.locator('tbody tr')
    await expect(rows).toHaveCount(2)
    await expect(rows.nth(0)).toContainText('zebra')
    await expect(rows.nth(1)).toContainText('alpha')

    await page.getByRole('button', { name: 'Name' }).click()

    await expect(rows.nth(0)).toContainText('alpha')
    await expect(rows.nth(1)).toContainText('zebra')
  })

  test('inline edit renames a tag in place', async ({ page }) => {
    let updateBody: unknown
    await page.route('**/api/tags/tag-z', (route) => {
      updateBody = route.request().postDataJSON()
      return route.fulfill(json({ id: 'tag-z', name: 'renamed' }))
    })

    await page.goto('/tags')
    const row = page.locator('[data-test="tag-row-tag-z"]')
    await row.getByRole('button', { name: 'Edit' }).click()
    await row.getByRole('textbox').fill('renamed')
    await row.getByRole('button', { name: 'Save' }).click()

    await expect(page.locator('[data-sonner-toast]')).toContainText('Updated to "renamed"')
    expect(updateBody).toEqual({ name: 'renamed' })
  })
})
