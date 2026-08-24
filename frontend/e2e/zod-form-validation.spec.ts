import { test, expect } from '@playwright/test'
import { mockApi } from './support/mockApi'

/**
 * Covers the vee-validate + zod form-validation pass: WorkspaceForm and
 * EditEntryPage now validate via a zod schema (matching the novo-mcp
 * blueprint's Form/FormField/FormMessage pattern) instead of manual
 * truthiness checks, surfacing errors inline next to each invalid field
 * and blocking the network call entirely.
 */
test.describe('Zod-backed form validation', () => {
  test.beforeEach(async ({ page }) => {
    await mockApi(page)
  })

  test('WorkspaceForm: empty name shows an inline error, dialog stays open, no request sent', async ({
    page,
  }) => {
    let created = false
    await page.route('**/api/workspaces', (route) => {
      if (route.request().method() === 'POST') created = true
      return route.fallback()
    })

    await page.goto('/workspaces')
    await page.locator('[data-test="ws-new"]').click()
    await page.locator('[data-test="ws-submit"]').click()

    await expect(page.getByText('Name is required')).toBeVisible()
    await expect(page.locator('[data-test="ws-name"]')).toBeVisible()
    expect(created).toBe(false)
  })

  test('EditEntryPage: clearing Title shows an inline error and blocks save', async ({ page }) => {
    let saved = false
    await page.route('**/api/entries/entry-1', (route) => {
      if (route.request().method() === 'PUT') saved = true
      return route.fallback()
    })

    await page.goto('/entries/entry-1/edit')
    await page.getByRole('button', { name: 'Classification' }).click()
    await page.getByLabel('Title').fill('')
    await page.getByRole('dialog').getByRole('button', { name: 'Save Changes' }).click()

    await expect(page.getByText('Title is required')).toBeVisible()
    await expect(page).toHaveURL(/\/entries\/entry-1\/edit$/)
    expect(saved).toBe(false)
  })
})
