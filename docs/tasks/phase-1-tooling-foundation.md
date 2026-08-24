# Phase 1 — Tooling Foundation

**Depends on:** Phase 0 (baseline recorded)
**Blocks:** Phase 2 onward (later phases assume lint/typecheck scripts exist)
**Risk:** low — config-only, no runtime/visual change

## Goal

Bring metamorphic-kb's linting, formatting, and TypeScript configuration up to the standard shared by `novo-mcp`, `document-generator-ui`, and `novo_review_tool`: ESLint flat config, Prettier, a split `tsconfig.json`/`tsconfig.app.json`/`tsconfig.node.json`, and the standard `package.json` script set (`lint`, `lint:check`, `format`, `typecheck`, `verify`). Nothing about the app's behavior or appearance changes in this phase — it's pure tooling.

## Current state

- `frontend/tsconfig.json` is a single flat file (`strict: true`, `moduleResolution: "Bundler"`, no path aliases).
- No ESLint config anywhere in `frontend/`.
- No `.prettierrc`.
- `package.json` scripts: `dev`, `build` (`vue-tsc --noEmit && vite build`), `preview`. No `lint`, `format`, `typecheck`, or `verify`.

## Reference pattern (all 3 sibling repos agree)

### `frontend/eslint.config.js` (flat config)
Adapt from `/Users/johncarroll/Documents/Repos/novo_review_tool/frontend/eslint.config.js`. Key characteristics:
- Plugins: `@typescript-eslint/eslint-plugin`, `eslint-plugin-vue`, `eslint-plugin-prettier` (defer `eslint-plugin-sonarjs` — see index.md deferred decisions)
- Parser: `@typescript-eslint/parser` for `.ts`, `vue-eslint-parser` for `.vue`
- Rules: single quotes (`avoidEscape`), no semicolons (delegated entirely to Prettier), trailing commas `always-multiline`, indentation rule off (Prettier owns it), `no-unused-vars` off (delegated to TS `noUnusedLocals`/`noUnusedParameters`), `vue/multi-word-component-names` off (metamorphic-kb has single-word-ish component names already, e.g. `SearchBar` is fine either way but don't force multi-word)
- Ignores: `.claude`, `dist`, `node_modules`

### `frontend/.prettierrc`
```json
{
  "semi": false,
  "tabWidth": 2,
  "printWidth": 100,
  "singleQuote": true,
  "trailingComma": "es5",
  "bracketSpacing": true,
  "endOfLine": "auto"
}
```

### `frontend/tsconfig.json` (references-only pattern)
```json
{
  "files": [],
  "references": [
    { "path": "./tsconfig.app.json" },
    { "path": "./tsconfig.node.json" }
  ]
}
```

### `frontend/tsconfig.app.json`
Contains the actual app compiler options: `strict: true`, `noUnusedLocals: true`, `noUnusedParameters: true`, `noFallthroughCasesInSwitch: true`, `skipLibCheck: true`, `target: "ES2020"`, `lib: ["ES2020", "DOM", "DOM.Iterable"]`, `include: ["src/**/*.ts", "src/**/*.d.ts", "src/**/*.vue"]`. **Add the path alias now** even though nothing uses `@/` yet — Phase 2 needs it immediately:
```json
"paths": { "@/*": ["./src/*"] }
```

### `frontend/tsconfig.node.json`
Standard Vite-config-only tsconfig (covers `vite.config.ts`), matching the reference repos' pattern.

### `package.json` scripts to add/update
```json
{
  "scripts": {
    "dev": "vite --host 0.0.0.0",
    "build": "vue-tsc -b && vite build",
    "preview": "vite preview --host 0.0.0.0",
    "typecheck": "vue-tsc -b --noEmit",
    "lint": "eslint . --fix",
    "lint:check": "eslint .",
    "format": "prettier --write src/",
    "verify": "npm run typecheck && npm run lint:check"
  }
}
```
Note: `verify` only runs typecheck+lint in this phase — `&& npm run test:unit` gets added in Phase 8 once Vitest exists.

### devDependencies to add
`@typescript-eslint/eslint-plugin`, `@typescript-eslint/parser`, `eslint`, `eslint-config-prettier`, `eslint-plugin-prettier`, `eslint-plugin-vue`, `vue-eslint-parser`, `prettier`. Bump `vue-tsc` to `^2.2.12` (from whatever version is currently pinned) to match the sibling repos.

## Files touched

**New:**
- `frontend/eslint.config.js`
- `frontend/.prettierrc`
- `frontend/tsconfig.app.json`
- `frontend/tsconfig.node.json`

**Modified:**
- `frontend/tsconfig.json` — rewritten to references-only
- `frontend/package.json` — scripts + devDependencies as above, `build` script changed from `vue-tsc --noEmit && vite build` to `vue-tsc -b && vite build`

## Expected friction

Turning on `noUnusedLocals`/`noUnusedParameters` plus ESLint's strict ruleset will likely surface small pre-existing issues in the current flat component files (unused imports, unused destructured props, etc.). This is expected — fix these as trivial cleanup within this phase; do not change any behavior while fixing them.

## Verification / Definition of Done

- [ ] `npm run typecheck` runs clean (zero errors)
- [ ] `npm run lint:check` runs clean (zero errors/warnings, or only pre-existing ones you've explicitly triaged)
- [ ] `npm run format` produces no unexpected diffs beyond whitespace/quote-style normalization — review the diff before committing
- [ ] `docker compose up --build` — app behaves identically to the Phase 0 baseline (this phase touches no `.vue`/runtime `.ts` logic, only config and possibly trivial unused-import cleanup)
- [ ] Re-run the Phase 0 click-through checklist to confirm nothing regressed
