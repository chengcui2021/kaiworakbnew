import { test, expect } from '@playwright/test'
import { mockApi } from './support/mockApi'

/**
 * Covers Phase 11, Story 17: switching Search's scope tab used to unmount
 * SearchBar and silently drop whatever the user had typed. Also verifies the
 * tabs are real, keyboard-operable ARIA tabs (Reka UI Tabs), not the earlier
 * plain-button + role="tablist" mimicry.
 */
test.describe('Search scope toggle', () => {
  test.beforeEach(async ({ page }) => {
    await mockApi(page)
  })

  test('typed query survives switching scope', async ({ page }) => {
    await page.goto('/search')

    await page.getByRole('tab', { name: 'All KB entries' }).click()
    await page.locator('[data-test="search-input"]').fill('unpersisted query text')

    await page.getByRole('tab', { name: 'Active workspace documents' }).click()
    await expect(page.locator('[data-test="search-input"]')).toHaveValue('unpersisted query text')

    await page.getByRole('tab', { name: 'All KB entries' }).click()
    await expect(page.locator('[data-test="search-input"]')).toHaveValue('unpersisted query text')
  })

  test('tabs are real ARIA tabs with correct selected state', async ({ page }) => {
    await page.goto('/search')

    const entriesTab = page.getByRole('tab', { name: 'All KB entries' })
    const workspaceTab = page.getByRole('tab', { name: 'Active workspace documents' })

    await workspaceTab.click()
    await expect(workspaceTab).toHaveAttribute('aria-selected', 'true')
    await expect(entriesTab).toHaveAttribute('aria-selected', 'false')

    await entriesTab.click()
    await expect(entriesTab).toHaveAttribute('aria-selected', 'true')
  })
})
