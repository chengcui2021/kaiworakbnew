import { test, expect } from '@playwright/test'
import { mockApi, json } from './support/mockApi'

/**
 * Covers the @tanstack/vue-table consistency pass: DocumentList.vue now
 * builds its rows via useVueTable (headless sorting) rendered through the
 * shadcn Table primitives, instead of a plain v-for, matching the novo-mcp
 * blueprint's data-grid pattern. Exercised via WorkspaceDetailPage, the one
 * page that renders DocumentList with full actions/approval/move enabled.
 */
test.describe('DocumentList data table', () => {
  test.beforeEach(async ({ page }) => {
    await mockApi(page)
    await page.route('**/api/workspaces/ws-1/documents*', (route) =>
      route.fulfill(
        json([
          {
            id: 'doc-a',
            workspace_id: 'ws-1',
            title: 'Zebra doc',
            content: 'zebra content',
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z',
            approval_status: 'draft',
          },
          {
            id: 'doc-b',
            workspace_id: 'ws-1',
            title: 'Alpha doc',
            content: 'alpha content',
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z',
            approval_status: 'approved',
          },
        ])
      )
    )
  })

  test('renders as a real table with sortable Title header', async ({ page }) => {
    await page.goto('/workspaces/ws-1')

    const table = page.locator('[data-test="document-list"]')
    await expect(table).toBeVisible()
    await expect(table.locator('thead th')).toHaveCount(4)

    const rows = table.locator('tbody tr')
    await expect(rows).toHaveCount(2)
    await expect(rows.nth(0)).toContainText('Zebra doc')
    await expect(rows.nth(1)).toContainText('Alpha doc')

    await page.getByRole('button', { name: 'Title' }).click()

    await expect(rows.nth(0)).toContainText('Alpha doc')
    await expect(rows.nth(1)).toContainText('Zebra doc')
  })

  test('per-row actions menu can set status', async ({ page }) => {
    let statusRequestBody: unknown
    await page.route('**/api/workspaces/ws-1/documents/doc-a/status', (route) => {
      statusRequestBody = route.request().postDataJSON()
      return route.fulfill(
        json({
          id: 'doc-a',
          workspace_id: 'ws-1',
          title: 'Zebra doc',
          content: 'zebra content',
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
          approval_status: 'approved',
        })
      )
    })

    await page.goto('/workspaces/ws-1')
    await page.locator('[data-test="doc-actions-doc-a"]').click()
    await page.locator('[data-test="doc-set-approved-doc-a"]').click()

    await expect(page.locator('[data-sonner-toast]')).toContainText('Status updated')
    expect(statusRequestBody).toEqual({ approval_status: 'approved' })
  })
})
