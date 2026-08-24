# Phase 3 — Design Tokens / Theme Migration

**Depends on:** Phase 2 (Tailwind + shadcn scaffolding must exist)
**Blocks:** Phase 4 (layout consumes these tokens), Phase 7 (component migration consumes semantic tokens)
**Risk:** low — additive, no component markup changes; old UI stays visually unaffected until Phase 4+

## Goal

Port the design tokens currently hard-coded in `frontend/src/style.css`'s `:root` block into the shadcn-vue semantic-colors/theme CSS structure used by all 3 sibling repos, and wire up dark-mode toggling. This is infrastructure only — no component's markup changes in this phase, so the running app looks the same as before (old UI still reads its own hard-coded values, not the new tokens).

## Current tokens to preserve

From `frontend/src/style.css`'s `:root` block (exact values may differ slightly — read the live file before starting):
```css
--bg: #0f172a
--surface: #ffffff
--surface-muted: #f1f5f9
--border: #e2e8f0
--text: #0f172a
--text-muted: #64748b
--primary: #2563eb
--primary-dark: #1d4ed8
--pass: #16a34a      /* used by ApprovalBadge/ValidationCheckItem for "pass" state */
--fail: #dc2626      /* used for "fail" state */
--warn: #d97706       /* used for "warn" state */
```
The `--pass`/`--fail`/`--warn` tokens map naturally onto shadcn's semantic `success`/`error`/`warning` tokens — **do not discard these values**, carry the actual hex/HSL colors forward into the new theme files so `ApprovalBadge.vue` and `ValidationCheckItem.vue` keep their current visual identity once migrated in Phase 7.

## Reference pattern (all 3 sibling repos agree)

### `frontend/styles/main.css`
```css
@import 'tailwindcss';
@import 'tw-animate-css';
@import './semantic-colors.css';
@import './themes/default.css';
@import './themes/default-dark.css';

@custom-variant dark (&:is(.dark *));

@theme {
  /* map CSS custom properties to Tailwind theme tokens */
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-card: var(--card);
  --color-card-foreground: var(--card-foreground);
  --color-popover: var(--popover);
  --color-popover-foreground: var(--popover-foreground);
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-foreground);
  --color-secondary: var(--secondary);
  --color-secondary-foreground: var(--secondary-foreground);
  --color-muted: var(--muted);
  --color-muted-foreground: var(--muted-foreground);
  --color-accent: var(--accent);
  --color-accent-foreground: var(--accent-foreground);
  --color-destructive: var(--destructive);
  --color-border: var(--border);
  --color-input: var(--input);
  --color-ring: var(--ring);
  --color-sidebar: var(--sidebar);
  --color-sidebar-foreground: var(--sidebar-foreground);
  --color-sidebar-primary: var(--sidebar-primary);
  --color-sidebar-accent: var(--sidebar-accent);
  --color-sidebar-border: var(--sidebar-border);
  --color-sidebar-ring: var(--sidebar-ring);
  --radius-sm: calc(var(--radius) - 4px);
  --radius-md: calc(var(--radius) - 2px);
  --radius-lg: var(--radius);
  --radius-xl: calc(var(--radius) + 4px);
}

* { @apply border-border; }
html, body { @apply bg-background text-foreground; }
```
(Read the actual file from `/Users/johncarroll/Documents/Repos/document-generator-ui/styles/main.css` or `/Users/johncarroll/Documents/Repos/novo-mcp/frontend/src/styles/main.css` for the exact full version — trim to only the token categories metamorphic-kb needs; skip chart-N tokens and multi-brand theme variants since this app doesn't need them.)

### `frontend/styles/semantic-colors.css`
Semantic token layer — success/error/warning/info, each with base + `-foreground` + `-muted` + `-hover` + `-muted-hover` variants. This is where `--pass`/`--fail`/`--warn` from the old `style.css` map to `success`/`error`/`warning`. Copy the structure from a reference repo (e.g. `novo_review_tool/frontend/src/styles/semantic-colors.css`) and substitute metamorphic-kb's actual brand colors for the base hues.

### `frontend/styles/themes/default.css` and `default-dark.css`
The actual color values (background/foreground/card/primary/etc. as HSL or OKLCH). **Reverse-engineer these from metamorphic-kb's existing `style.css` `:root` block** rather than taking the reference repos' generic shadcn neutrals wholesale — this is the key step that preserves the app's current visual identity through the migration. Map:
- `--bg` → `--background`
- `--surface` → `--card` / `--popover`
- `--text` → `--foreground`
- `--text-muted` → `--muted-foreground`
- `--primary` / `--primary-dark` → `--primary` (light/dark variants)
- `--border` → `--border`

For `default-dark.css`, since metamorphic-kb has no existing dark-mode palette, derive reasonable dark values (invert lightness, keep hue/saturation close to the light variant) or adapt directly from a reference repo's `default-dark.css` if the aesthetic doesn't need to be bespoke.

### Dark mode wiring
Add `@vueuse/core` and call `useColorMode()` in `frontend/src/main.ts` (simplest — matches the `novo-mcp` pattern, no bespoke composable needed):
```typescript
import { useColorMode } from '@vueuse/core'
// inside app setup, before mount:
useColorMode({ selector: 'html', attribute: 'class', modes: { light: '', dark: 'dark' } })
```

## Files touched

**New:**
- `frontend/styles/main.css`
- `frontend/styles/semantic-colors.css`
- `frontend/styles/themes/default.css`
- `frontend/styles/themes/default-dark.css`

**Modified:**
- `frontend/package.json` — add `@vueuse/core`
- `frontend/src/main.ts` — `useColorMode()` setup, and the `import './styles/main.css'` line if not already added in Phase 2
- `frontend/src/style.css` — **left in place, unmodified**. Not yet deleted; deletion happens at the end of Phase 7 once no component references its selectors anymore.

## Verification / Definition of Done

- [ ] `npm run build` succeeds
- [ ] In devtools, manually toggle the `.dark` class on `<html>` and confirm the new CSS custom properties (`--background`, `--foreground`, etc.) resolve to the expected light/dark values via "Computed" styles inspection
- [ ] The running app is **visually unchanged** from Phase 0/2 baseline — old UI doesn't consume the new tokens yet, so this phase should be invisible when just clicking through the app normally
- [ ] `npm run typecheck` and `npm run lint:check` still pass
