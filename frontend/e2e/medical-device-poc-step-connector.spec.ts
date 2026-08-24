import { test, expect } from '@playwright/test'
import { mockApi } from './support/mockApi'

/**
 * Covers Phase 12, Story 24: a thin visual connector between the Medical
 * Device PoC's five step cards, reinforcing they're one sequential flow.
 */
test.describe('Medical Device PoC step connector', () => {
  test.beforeEach(async ({ page }) => {
    await mockApi(page)
  })

  test('a connector renders between each of the five step cards', async ({ page }) => {
    await page.goto('/medical-device-poc')

    await expect(page.locator('[data-test="mdp-step-1"]')).toBeVisible()
    await expect(page.locator('[data-test="mdp-step-5"]')).toBeVisible()
    await expect(page.locator('[data-test="mdp-step-connector"]')).toHaveCount(4)
  })
})
