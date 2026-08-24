import { fileURLToPath, URL } from 'node:url'
import { defineConfig, mergeConfig, configDefaults } from 'vitest/config'
import viteConfig from './vite.config'

export default mergeConfig(
  viteConfig,
  defineConfig({
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    test: {
      environment: 'jsdom',
      setupFiles: ['./src/test-setup.ts'],
      // Keep Playwright e2e specs out of the Vitest run — they use the
      // Playwright test API, not Vitest. Run them with `npm run test:e2e`.
      exclude: [...configDefaults.exclude, '**/e2e/**'],
      coverage: {
        provider: 'v8',
        exclude: [...(configDefaults.coverage?.exclude ?? []), 'src/components/ui/**'],
        // No enforced threshold yet — this phase starts from 0% coverage and
        // only covers services/workspace.ts. Ratchet a real threshold up as
        // more of the codebase gets test coverage; don't set an aspirational
        // number that would immediately fail CI.
      },
    },
  })
)
