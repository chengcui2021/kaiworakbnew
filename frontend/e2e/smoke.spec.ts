import { test, expect } from '@playwright/test'
import { mockApi } from './support/mockApi'

/**
 * P0 — shell smoke. Proves the harness works end-to-end: the app boots, the
 * router mounts, and each of the 6 routes paints its heading — all against
 * the mocked API boundary, no backend required. Deeper feature journeys
 * (create/approve/move/delete) go in their own *.spec.ts files.
 */
test.describe('App shell (smoke)', () => {
  test.beforeEach(async ({ page }) => {
    await mockApi(page)
  })

  test('/ redirects to /workspaces and renders', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveURL(/\/workspaces$/)
    await expect(page.getByRole('heading', { name: 'Workspaces' })).toBeVisible()
  })

  test('/workspaces renders', async ({ page }) => {
    await page.goto('/workspaces')
    await expect(page.getByRole('heading', { name: 'Workspaces' })).toBeVisible()
  })

  test('/workspaces/:id renders the workspace name', async ({ page }) => {
    await page.goto('/workspaces/ws-1')
    await expect(page.getByRole('heading', { name: 'Demo Workspace' })).toBeVisible()
  })

  test('/approved renders', async ({ page }) => {
    await page.goto('/approved')
    await expect(page.getByRole('heading', { name: /Approved Knowledge/ })).toBeVisible()
  })

  test('/packages renders', async ({ page }) => {
    await page.goto('/packages')
    await expect(page.getByRole('heading', { name: /Context Packages/ })).toBeVisible()
  })

  test('/search renders', async ({ page }) => {
    await page.goto('/search')
    await expect(page.getByRole('heading', { name: 'Search' })).toBeVisible()
  })

  test('/medical-device-poc renders', async ({ page }) => {
    await page.goto('/medical-device-poc')
    await expect(page.getByRole('heading', { name: /Medical Device POC/ })).toBeVisible()
  })

  test('/submit renders', async ({ page }) => {
    await page.goto('/submit')
    await expect(page.getByRole('heading', { name: 'Submit entry' })).toBeVisible()
  })

  test('/browse renders', async ({ page }) => {
    await page.goto('/browse')
    await expect(page.getByRole('heading', { name: 'Browse entries' })).toBeVisible()
  })

  test('/tags renders', async ({ page }) => {
    await page.goto('/tags')
    await expect(page.getByRole('heading', { name: 'Tag management' })).toBeVisible()
  })

  test('/entries/:id/edit renders and keeps Browse Entries highlighted', async ({ page }) => {
    await page.goto('/entries/entry-1/edit')
    await expect(page.getByRole('heading', { name: 'Edit entry' })).toBeVisible()
    await expect(
      page.locator('[data-slot="sidebar"]').getByRole('link', { name: 'Browse Entries' })
    ).toHaveAttribute('data-active', 'true')
  })
})
