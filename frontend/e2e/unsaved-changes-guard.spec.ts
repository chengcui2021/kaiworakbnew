import { test, expect } from '@playwright/test'
import { mockApi } from './support/mockApi'

/**
 * Covers Phase 11, Story 16: navigating away from Submit Entry with unsaved
 * text should prompt via the app's confirm dialog, not silently discard.
 */
test.describe('Unsaved changes guard', () => {
  test.beforeEach(async ({ page }) => {
    await mockApi(page)
  })

  test('prompts on in-app navigation with unsaved edits, Stay keeps you on the page', async ({
    page,
  }) => {
    await page.goto('/submit')
    await page.getByLabel('Title').fill('Draft I have not saved yet')

    await page.getByRole('link', { name: 'Browse Entries' }).click()

    await expect(page.getByRole('alertdialog')).toBeVisible()
    await expect(page.getByRole('alertdialog')).toContainText('unsaved changes')

    await page.getByRole('button', { name: 'Stay on this page' }).click()
    await expect(page.getByRole('alertdialog')).toBeHidden()
    await expect(page).toHaveURL(/\/submit$/)
    await expect(page.getByLabel('Title')).toHaveValue('Draft I have not saved yet')
  })

  test('Leave without saving navigates away and discards the draft', async ({ page }) => {
    await page.goto('/submit')
    await page.getByLabel('Title').fill('Draft I have not saved yet')

    await page.getByRole('link', { name: 'Browse Entries' }).click()
    await expect(page.getByRole('alertdialog')).toBeVisible()

    await page.getByRole('button', { name: 'Leave without saving' }).click()
    await expect(page).toHaveURL(/\/browse$/)
  })

  test('no prompt when navigating away with a clean form', async ({ page }) => {
    await page.goto('/submit')
    await page.getByRole('link', { name: 'Browse Entries' }).click()
    await expect(page).toHaveURL(/\/browse$/)
  })
})
