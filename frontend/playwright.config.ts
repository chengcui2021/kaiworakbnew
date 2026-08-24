import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright e2e config — kept entirely separate from the Vitest unit suite.
 * Run with `npm run test:e2e`.
 *
 * The smoke suite mocks the backend at the network boundary (`page.route`) so
 * it's deterministic and doesn't need a running backend or docker compose.
 */
export default defineConfig({
  testDir: './e2e',
  testMatch: '**/*.spec.ts',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? [['html', { open: 'never' }], ['list']] : 'list',

  use: {
    // Vite's dev server always binds to 5173 (see vite.config.ts); the
    // webServer block below starts it via `npm run dev`.
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],

  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
})
