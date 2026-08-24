import { test, expect } from '@playwright/test'
import { mockApi, json } from './support/mockApi'

/**
 * Covers Phase 12, Story 22: EditEntryPage's right column reorganized into
 * labeled sub-sections, the Status select split into Lifecycle/Publish
 * groups, and Delete given its own row separate from Cancel/Save.
 *
 * Later reworked so Classification/Links & Tags live in a slide-in Sheet
 * (opened via the "Classification" button) instead of a fixed right column,
 * freeing full width for the split content editor.
 *
 * Later still: Delete/Cancel/Save Changes all moved into a single action bar
 * at the top of the page (Delete first, then Cancel, then Save Changes),
 * reachable without scrolling — the old bottom "Actions" card is gone. Save
 * Changes is duplicated inside the Classification Sheet's own footer since
 * those fields live behind the Sheet.
 */
test.describe('Edit entry form organization', () => {
  test.beforeEach(async ({ page }) => {
    await mockApi(page)
  })

  test('Classification sheet reads as distinct labeled sub-sections', async ({ page }) => {
    await page.goto('/entries/entry-1/edit')

    await page.getByRole('button', { name: 'Classification' }).click()
    await expect(page.getByRole('heading', { name: 'Classification' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Links & Tags' })).toBeVisible()
  })

  test('Classification sheet has its own Save Changes button that saves without closing first', async ({
    page,
  }) => {
    let saved = false
    await page.route('**/api/entries/entry-1', (route) => {
      if (route.request().method() === 'PUT') {
        saved = true
        return route.fulfill(
          json({
            id: 'entry-1',
            type: 'documentation',
            component: 'api',
            title: 'Updated title',
            content: 'Seeded for e2e smoke tests',
            source: null,
            author: 'e2e',
            status: 'open',
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z',
            tags: [],
          })
        )
      }
      return route.fallback()
    })

    await page.goto('/entries/entry-1/edit')
    await page.getByRole('button', { name: 'Classification' }).click()
    await page.getByLabel('Title').fill('Updated title')
    await page.getByRole('dialog').getByRole('button', { name: 'Save Changes' }).click()

    await expect.poll(() => saved).toBe(true)
    await expect(page).toHaveURL(/\/browse$/)
  })

  test('Status select groups lifecycle and publish statuses separately', async ({ page }) => {
    await page.goto('/entries/entry-1/edit')

    await page.getByRole('button', { name: 'Classification' }).click()
    await page.getByLabel('Status').click()
    await expect(page.getByText('Lifecycle', { exact: true })).toBeVisible()
    await expect(page.getByText('Publish', { exact: true })).toBeVisible()
    await expect(page.getByRole('option', { name: 'open' })).toBeVisible()
    await expect(page.getByRole('option', { name: 'published' })).toBeVisible()
  })

  test('Top action bar orders Delete entry before Cancel and Save Changes, and Delete still confirms', async ({
    page,
  }) => {
    await page.goto('/entries/entry-1/edit')

    const deleteButton = page.locator('[data-test="edit-top-delete"]')
    const cancelButton = page.locator('[data-test="edit-top-cancel"]')
    const saveButton = page.locator('[data-test="edit-top-save"]')
    await expect(deleteButton).toBeVisible()
    await expect(cancelButton).toBeVisible()
    await expect(saveButton).toBeVisible()

    const deleteBox = await deleteButton.boundingBox()
    const cancelBox = await cancelButton.boundingBox()
    const saveBox = await saveButton.boundingBox()
    expect(deleteBox).not.toBeNull()
    expect(cancelBox).not.toBeNull()
    expect(saveBox).not.toBeNull()
    // Delete entry sits before Cancel, which sits before Save Changes.
    expect(deleteBox!.x).toBeLessThan(cancelBox!.x)
    expect(cancelBox!.x).toBeLessThan(saveBox!.x)

    await deleteButton.click()
    await expect(page.getByRole('alertdialog')).toBeVisible()

    await page.route('**/api/entries/entry-1', (route) => route.fulfill({ status: 204 }))
    await page.getByRole('alertdialog').getByRole('button', { name: 'Delete entry' }).click()
    await expect(page).toHaveURL(/\/browse$/)
  })

  test('Save Changes is reachable from the top of the page, without scrolling', async ({
    page,
  }) => {
    let saved = false
    await page.route('**/api/entries/entry-1', (route) => {
      if (route.request().method() === 'PUT') {
        saved = true
        return route.fulfill(
          json({
            id: 'entry-1',
            type: 'documentation',
            component: 'api',
            title: 'Updated from top bar',
            content: 'Seeded for e2e smoke tests',
            source: null,
            author: 'e2e',
            status: 'open',
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z',
            tags: [],
          })
        )
      }
      return route.fallback()
    })

    await page.goto('/entries/entry-1/edit')

    const topSave = page.locator('[data-test="edit-top-save"]')
    await expect(topSave).toBeVisible()

    await topSave.click()
    await expect.poll(() => saved).toBe(true)
    await expect(page).toHaveURL(/\/browse$/)
  })
})
