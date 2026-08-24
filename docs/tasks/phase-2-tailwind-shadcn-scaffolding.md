# Phase 2 — Tailwind v4 + shadcn-vue Scaffolding

**Depends on:** Phase 1 (path alias `@/*` must already exist in `tsconfig.app.json`)
**Blocks:** Phase 3 (theme tokens build on this), Phase 4 (layout needs shadcn primitives)
**Risk:** low — additive only, old CSS keeps winning the cascade

## Goal

Install Tailwind CSS v4 and the shadcn-vue plumbing (`components.json`, `cn()` utility, path alias wiring, a small set of initial primitives) as a **purely additive layer**. The existing `frontend/src/style.css` (~15KB hand-written CSS) stays fully in place and continues to be imported — nothing is deleted or replaced yet. By the end of this phase the app should be visually indistinguishable from the Phase 0 baseline.

## Reference pattern (all 3 sibling repos agree)

### `frontend/components.json`
```json
{
  "$schema": "https://shadcn-vue.com/schema.json",
  "style": "new-york",
  "typescript": true,
  "tailwind": {
    "config": "",
    "css": "styles/main.css",
    "baseColor": "neutral",
    "cssVariables": true,
    "prefix": ""
  },
  "aliases": {
    "components": "@/components",
    "composables": "@/composables",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib"
  },
  "iconLibrary": "lucide"
}
```
Note `"css": "styles/main.css"` — that file doesn't exist yet (created in Phase 3), but shadcn-vue's CLI needs this path declared now so `npx shadcn-vue@latest add <component>` works correctly.

### `frontend/src/lib/utils.ts`
```typescript
import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```
Identical across all 3 reference repos — copy verbatim.

### `frontend/postcss.config.cjs`
```js
module.exports = {
  plugins: {
    autoprefixer: {},
  },
}
```
Tailwind v4 doesn't need a PostCSS plugin entry (handled by `@tailwindcss/vite`) — this file only needs autoprefixer.

### `frontend/vite.config.ts` changes
Add the Tailwind Vite plugin and the `@` path alias (mirroring the `@/*` TS path alias from Phase 1):
```typescript
import { fileURLToPath, URL } from 'node:url'
import tailwindcss from '@tailwindcss/vite'
// ...existing imports (vue plugin, defineConfig, etc.)

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  // ...keep the existing server.proxy config for /api and /health untouched
})
```
**Important:** do not touch the existing `server.proxy` block (`/api` → `VITE_PROXY_TARGET`, `/health` → same) — that's load-bearing for the Docker setup and unrelated to this phase.

### Initial shadcn-vue primitives
Run (requires network access; if unavailable, hand-scaffold from the reference repos' `src/components/ui/{button,card,input,label}/` instead):
```bash
cd frontend && npx shadcn-vue@latest add button card input label
```
Keep the initial set minimal — `sidebar`, `breadcrumb`, `separator`, `sonner` are deferred to Phase 4 when the layout actually needs them.

### `frontend/src/main.ts` change
Add a **second** CSS import alongside the existing one — both load, nothing conflicts yet since no component references Tailwind utility classes:
```typescript
import './style.css'        // existing — keep as-is for now
import './styles/main.css'  // new — added in Phase 3, but the import can be added here now as a no-op if the file doesn't exist yet; alternatively defer this exact line to Phase 3 if you'd rather not import a nonexistent file
```
**Note:** `styles/main.css` is actually created in Phase 3, not this phase. If you want Phase 2 to be independently buildable, skip this `main.ts` edit here and do it as the first step of Phase 3 instead — either ordering is fine since Phase 2 and 3 are typically done back-to-back.

### package.json dependencies to add
- `@tailwindcss/vite`
- `tailwindcss`
- `tailwind-merge`
- `class-variance-authority`
- `clsx`
- `reka-ui`
- `lucide-vue-next`
- `tw-animate-css`
- devDependency: `autoprefixer`

## Files touched

**New:**
- `frontend/components.json`
- `frontend/src/lib/utils.ts`
- `frontend/postcss.config.cjs`
- `frontend/src/components/ui/{button,card,input,label}/*.vue` (+ `index.ts` barrel files per shadcn-vue convention)

**Modified:**
- `frontend/vite.config.ts` — add `@tailwindcss/vite` plugin + `@` alias
- `frontend/package.json` — add the dependencies listed above
- `frontend/src/main.ts` — (optional this phase, see note above) add `styles/main.css` import

## Verification / Definition of Done

- [ ] `npm install` succeeds with the new dependencies
- [ ] `npm run build` succeeds with the new Tailwind Vite plugin active
- [ ] `docker compose up --build` — existing UI renders **pixel-identical** to the Phase 0 baseline (old `style.css` cascade still wins since nothing consumes Tailwind classes yet)
- [ ] Sanity-check shadcn wiring: temporarily drop a `<Button>Test</Button>` into any page, confirm it renders styled (proves `cn()`, Tailwind, and the new primitive are wired correctly end-to-end), then revert that temporary change before committing
- [ ] `npm run typecheck` and `npm run lint:check` still pass
