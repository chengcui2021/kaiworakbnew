import { test, expect } from '@playwright/test'
import { mockApi, json } from './support/mockApi'

/**
 * Covers the Alert→toast consistency pass across Submit Entry and the
 * workspace-scoped pages: transient action results (submit/create/save) now
 * go through vue-sonner toast(), while persistent/blocking state (no
 * workspace selected, list failed to load) stays as an inline Alert with a
 * real lucide icon instead of a typed unicode character.
 */
test.describe('Toast feedback and persistent Alert icons', () => {
  test.beforeEach(async ({ page }) => {
    await mockApi(page)
  })

  test('Submit Entry: success toast includes a "View entry" action that navigates', async ({
    page,
  }) => {
    await page.route('**/api/entries', (route) => {
      if (route.request().method() === 'POST') {
        return route.fulfill(
          json({
            id: 'entry-new',
            type: 'documentation',
            component: 'api',
            title: 'New entry',
            content: 'Some content',
            source: null,
            author: 'e2e',
            status: 'open',
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z',
            tags: [],
          })
        )
      }
      return route.fulfill(json({ entries: [], total: 0, limit: 20, offset: 0 }))
    })

    await page.goto('/submit')
    await page.getByLabel('Title').fill('New entry')
    const content = page.getByLabel('Content', { exact: true })
    await content.click()
    await page.keyboard.type('Some content')
    await page.getByLabel('Author').fill('e2e')
    await page.getByRole('button', { name: 'Submit entry' }).click()

    const toast = page.locator('[data-sonner-toast]')
    await expect(toast).toContainText('Entry created')
    await toast.getByRole('button', { name: 'View entry' }).click()
    await expect(page).toHaveURL(/\/entries\/entry-new\/edit$/)
  })

  test('Submit Entry: empty required fields show inline zod validation errors, no submission', async ({
    page,
  }) => {
    let submitted = false
    await page.route('**/api/entries', (route) => {
      if (route.request().method() === 'POST') submitted = true
      return route.fulfill(json({ entries: [], total: 0, limit: 20, offset: 0 }))
    })

    await page.goto('/submit')
    await page.getByRole('button', { name: 'Submit entry' }).click()

    await expect(page.getByText('Title is required')).toBeVisible()
    await expect(page.getByText('Content is required')).toBeVisible()
    await expect(page.getByText('Author is required')).toBeVisible()
    await expect(page).toHaveURL(/\/submit$/)
    expect(submitted).toBe(false)
  })

  test('Workspaces: creating a workspace shows a success toast', async ({ page }) => {
    await page.route('**/api/workspaces', (route) => {
      if (route.request().method() === 'POST') {
        return route.fulfill(
          json({
            id: 'ws-2',
            name: 'New workspace',
            description: '',
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z',
            document_count: 0,
          })
        )
      }
      return route.fulfill(
        json([
          {
            id: 'ws-1',
            name: 'Demo Workspace',
            description: '',
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z',
            document_count: 0,
          },
        ])
      )
    })

    await page.goto('/workspaces')
    await page.locator('[data-test="ws-new"]').click()
    await page.getByLabel('Name').fill('New workspace')
    await page.locator('[data-test="ws-submit"]').click()

    await expect(page.locator('[data-sonner-toast]')).toContainText('Created workspace')
  })

  test('Approved Knowledge: no-workspace state renders as a persistent Alert with an icon', async ({
    page,
  }) => {
    await page.route('**/api/workspaces', (route) => route.fulfill(json([])))

    await page.goto('/approved')

    const alert = page.locator('[data-test="no-workspace"]')
    await expect(alert).toBeVisible()
    await expect(alert.locator('svg')).toBeVisible()
    await expect(alert.getByText('No workspace selected')).toBeVisible()
  })

  test('Approved Knowledge: load failure renders as a persistent Alert with an icon', async ({
    page,
  }) => {
    await page.route('**/api/workspaces/ws-1/documents*', (route) =>
      route.fulfill({ status: 500, contentType: 'application/json', body: '{}' })
    )

    await page.goto('/approved')

    const alert = page.getByRole('alert')
    await expect(alert).toBeVisible()
    await expect(alert.locator('svg')).toBeVisible()
    await expect(alert).toContainText("Couldn't load approved knowledge")
  })
})
