# Phase 9 — Claude Code Tooling

**Depends on:** Phase 5 (Pinia), Phase 6 (useAPI.ts/services), Phase 8 (Vitest) — hooks/skills reference all of this infrastructure
**Blocks:** nothing — this is the last phase
**Risk:** low — additive tooling, doesn't touch app runtime code (except deleting two legacy guidance docs)

## Goal

Install the `.claude/skills/frontend/`, `.claude/hooks/`, `.claude/commands/`, root `CLAUDE.md` + `frontend/CLAUDE.md`, and `.claude/settings.json` that all 3 sibling repos share byte-for-byte. This is deliberately the **last** phase: the hooks (`inject-test-context.mjs`, `run-tests-after-edit.sh`, `enforce-verify.mjs`) and several skills (`testing`, `test-coverage`, `api-service-layer`, `vue-pinia`, `shadcn-vue`) assume infrastructure — Vitest, Pinia stores, `useAPI.ts` services, `components.json` — that doesn't exist until Phases 5–8 land. Installing them earlier means skills point at nonexistent patterns and hooks fail or silently no-op.

## Source of truth for copying

Copy from `/Users/johncarroll/Documents/Repos/novo_review_tool/.claude/` — confirmed as the most complete reference copy (7 hook registrations vs. 6 in the other two repos, includes `pre-pr-check.mjs` which the others lack).

## What to install

### `.claude/skills/frontend/`
Copy these skill directories wholesale (each with its `SKILL.md` + any `reference/`/`assets/` subdirs):
`project`, `shadcn-vue`, `api-service-layer`, `vue-pinia`, `vue3-typescript`, `vue-router`, `tailwind`, `testing`, `test-coverage`, `e2e`, `linting`, `permissions`, `weekly-coverage-check`

**Skip initially:** `vee-validate`, `tanstack-table`, `tiptap-editor` — metamorphic-kb doesn't use these libraries (Phase 7 explicitly avoided TanStack Table; `vee-validate` is conditional on Phase 7's form-complexity decision). Only add the corresponding skill if the library actually gets adopted.

### `.claude/hooks/`
Copy verbatim (these are generic, not app-specific, except where noted):
- `SessionStart`: `prime-context.mjs`
- `PreToolUse`: `protect-sensitive.mjs`, `check-critical-files.sh` — **these need editing**, see below
- `PostToolUse`: `run-tests-after-edit.sh`, `inject-test-context.mjs`, `inject-skill-pointers.mjs`, `inject-lint-results.mjs`, `inject-e2e-context.mjs`
- `Stop`: `enforce-verify.mjs`, `run-tests-on-stop.sh`
- Plus each hook's `.test.mjs` sibling if present in the source

### `.claude/commands/fix-problems.md`
Copy verbatim — sweeps ESLint/TypeScript diagnostics and applies fixes.

### `.claude/settings.json` + `.claude/settings.local.json`
Copy and adapt: permissions allowlist, MCP server entries (shadcn-vue MCP, tailwindcss MCP if useful here).

### Root `CLAUDE.md`
Short pointer file to `frontend/CLAUDE.md`, adapted for metamorphic-kb's actual backend (FastAPI/Python, not whatever the reference repos' backend is).

### `frontend/CLAUDE.md`
Adapted Change Protocol:
1. Read the sibling `*.test.ts` file before changing code
2. Cherry-pick relevant skills from `.claude/skills/frontend/`
3. Do the work
4. Run `npm run verify`
5. Update tests + `UNTESTED.md`

**P0 files for metamorphic-kb** (edit the hardcoded list — this app has no auth, so the reference repos' auth-file P0 list doesn't apply):
- `frontend/src/stores/workspace.ts`
- `frontend/src/services/useAPI.ts`
- `frontend/src/services/useWorkspaceService.ts`

Document coverage tiers (whatever was actually established in Phase 8 — don't just copy the reference repos' mature P0 95/90 numbers if Phase 8 started more conservative).

## Required edits to copied hooks

`protect-sensitive.mjs` and `check-critical-files.sh` both hardcode a P0-file list (the reference repos' list is auth-related: `stores/auth.ts`, `services/useAuthService.ts`, `composables/useAuth.ts`, etc. — none of which exist in metamorphic-kb). Edit both files' hardcoded lists to metamorphic-kb's actual P0 files listed above.

## Legacy docs to delete

`frontend/.claude/FRONTEND_STRUCTURE.md` and `backend/.claude/BACKEND_STRUCTURE.md` — **delete both** (confirmed with the team during planning). These are one-shot starter-template generation prompts (they literally read like "Product: Continue KB Phase 1... Idea: Continue KB Phase 1.5..." instructions to an initial code-gen pass, not durable team conventions), and they now actively conflict with the new setup — e.g. `FRONTEND_STRUCTURE.md` says API wrappers belong in `frontend/src/api/index.ts`, which Phase 6 deleted. Leaving them in place risks a future agent session reading stale, contradictory guidance instead of the new `CLAUDE.md`.

If any of their content still has product/requirements value (the "Continue KB Phase 1.5" feature requirements around search scoping, workspace validation, activity display), that context has already been captured in this repo's existing `docs/` directory (`docs/prototype-spec.md`, `docs/evolution-requirements.md`) — verify before deleting that nothing unique is lost, but don't preserve the `.claude/`-located copies once confirmed redundant.

## Files touched

**New:**
- `.claude/skills/frontend/{project,shadcn-vue,api-service-layer,vue-pinia,vue3-typescript,vue-router,tailwind,testing,test-coverage,e2e,linting,permissions,weekly-coverage-check}/`
- `.claude/hooks/*` (listed above)
- `.claude/commands/fix-problems.md`
- `.claude/settings.json`, `.claude/settings.local.json`
- `CLAUDE.md` (root)
- `frontend/CLAUDE.md`

**Modified:**
- `.claude/hooks/protect-sensitive.mjs`, `.claude/hooks/check-critical-files.sh` — P0 file list edited to metamorphic-kb's actual critical files

**Deleted:**
- `frontend/.claude/FRONTEND_STRUCTURE.md`
- `backend/.claude/BACKEND_STRUCTURE.md`

## Verification / Definition of Done

- [ ] Start a fresh Claude Code session in the repo root — `SessionStart` hook (`prime-context.mjs`) fires without error and shows branch/status context
- [ ] Make a trivial edit to a P0 file (e.g. `frontend/src/stores/workspace.ts`) — confirm `protect-sensitive.mjs` prompts for confirmation before allowing the edit
- [ ] Make a normal (non-P0) edit — confirm `inject-test-context.mjs` and `inject-lint-results.mjs` inject useful sibling-test/lint context
- [ ] Attempt to stop the session with uncommitted `src/` changes and no `verify` run since the last edit — confirm `enforce-verify.mjs` blocks the stop
- [ ] Both legacy `FRONTEND_STRUCTURE.md`/`BACKEND_STRUCTURE.md` files confirmed deleted and their content cross-checked against `docs/prototype-spec.md`/`docs/evolution-requirements.md` for redundancy first
- [ ] `git config core.hooksPath .githooks` wired (matching reference repos' pre-push enforcement), and `.githooks/pre-push` added if not already present from an earlier phase
