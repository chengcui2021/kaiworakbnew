import { test, expect } from '@playwright/test'
import { mockApi, json } from './support/mockApi'

/**
 * Covers the Alert→toast consistency pass: TagsPanel and JiraLinksPanel now
 * report transient add/remove feedback via vue-sonner toast() calls instead
 * of a persistent inline Alert, matching the novo-mcp blueprint's pattern of
 * reserving Alert for persistent/blocking state and toast for action results.
 */
test.describe('Panel toast feedback', () => {
  test.beforeEach(async ({ page }) => {
    await mockApi(page)
  })

  test('TagsPanel: successful add shows a success toast', async ({ page }) => {
    await page.route('**/api/entries/entry-1/tags', (route) => {
      if (route.request().method() === 'POST') {
        return route.fulfill(
          json({
            id: 'tag-2',
            name: 'onboarding',
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z',
          })
        )
      }
      return route.fulfill(json({ entry_id: 'entry-1', tags: [], count: 0 }))
    })

    await page.goto('/entries/entry-1/edit')
    await page.getByRole('button', { name: 'Classification' }).click()
    await page.locator('input[placeholder="e.g. api, onboarding"]').fill('onboarding')
    await page.getByRole('button', { name: 'Add tag' }).click()

    await expect(page.locator('[data-sonner-toast]')).toContainText('Tagged with "onboarding"')
  })

  test('TagsPanel: failed add shows an error toast', async ({ page }) => {
    await page.route('**/api/entries/entry-1/tags', (route) => {
      if (route.request().method() === 'POST') {
        return route.fulfill({ status: 500, contentType: 'application/json', body: '{}' })
      }
      return route.fulfill(json({ entry_id: 'entry-1', tags: [], count: 0 }))
    })

    await page.goto('/entries/entry-1/edit')
    await page.getByRole('button', { name: 'Classification' }).click()
    await page.locator('input[placeholder="e.g. api, onboarding"]').fill('broken')
    await page.getByRole('button', { name: 'Add tag' }).click()

    const toast = page.locator('[data-sonner-toast]')
    await expect(toast).toBeVisible()
    await expect(toast).toHaveAttribute('data-type', 'error')
  })

  test('JiraLinksPanel: successful link shows a success toast', async ({ page }) => {
    await page.route('**/api/entries/entry-1/jira-links', (route) => {
      if (route.request().method() === 'POST') {
        return route.fulfill(
          json({ jira_key: 'PROJ-123', title: null, status: null, issue_type: null })
        )
      }
      return route.fulfill(json({ entry_id: 'entry-1', links: [], count: 0 }))
    })

    await page.goto('/entries/entry-1/edit')
    await page.getByRole('button', { name: 'Classification' }).click()
    await page.locator('input[placeholder="e.g. PROJ-123"]').fill('PROJ-123')
    await page.getByRole('button', { name: 'Link', exact: true }).click()

    await expect(page.locator('[data-sonner-toast]')).toContainText('Linked PROJ-123')
  })
})
