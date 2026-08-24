# Project Instructions

> **This is a business-critical app.** Correctness and not breaking existing behavior outrank speed. Follow the Change Protocol below on every code change.

## Tech Stack

- **Frontend:** Vue 3 (Composition API), TypeScript, Vite, Tailwind, Pinia — code lives in `src/`
- **Backend:** Python, FastAPI — code lives in `../backend/`

This app has **no authentication** — unlike the sibling repos this pattern was
copied from, there is no P0 auth/session layer. The P0 tier here is the
shared state + base/domain API layer instead (see below).

## Change Protocol

Follow these steps, in order, for **any** change to code under `src/` (especially `pages/` / `composables/` / `stores/` / `services/`):

1. **Read the tests first.** Before editing a file, read its sibling `.test.ts` if one exists — the assertions are the behavioral contract. (A `PostToolUse` hook also injects the sibling test into context *after* your first edit, with a directive to reconcile and run it — but read it up front; don't wait for the hook.) Also consider the **blast radius**: a composable/store/service change can break its consumer pages — check what depends on what you're touching, not just the edited file.
2. **Cherry-pick the relevant skills.** Load only the `frontend-standards` plugin skills that match the change (see the list under Frontend Development) — not the whole folder. This keeps context focused. Each skill's frontmatter `WHEN`/`WHEN NOT` tells you if it applies.
3. **Do the work**, adhering to those skills' conventions.
4. **Verify.** Run the sibling test(s) (`npx vitest run <path>`) and `npx vue-tsc --noEmit`. For changes touching a P0 file or shared infrastructure, run the full suite (`npm run verify`). Report pass/fail honestly — never claim done on unrun tests.
5. **Leave the safety net stronger.** Update/extend tests for the behavior you changed or added, and update [`UNTESTED.md`](UNTESTED.md) (check off / add entries). New files under `pages/`/`composables/`/`stores/`/`services/` must ship a sibling `.test.ts` **or** get an `UNTESTED.md` entry.

**Hard rules:**
- **Breaking an assertion is a deliberate change, never a silent one.** Update the test in the same change and explain why. If the change would break a **P0** contract, *stop and confirm intent* before altering the test.
- **Respect the coverage tiers** in `UNTESTED.md` and the anti-vanity rule in the `test-coverage` skill — cover real behavior (happy path + one error per endpoint), not brittle "renders without error" tests.

**P0 files** (everything else depends on these — a contract change must be intentional and confirmed):
- `frontend/src/stores/workspace.ts`
- `frontend/src/services/useAPI.ts`
- `frontend/src/services/useWorkspaceService.ts`

**Coverage:** `vitest.config.ts` has no enforced threshold yet — this app started Phase 8 at 0% coverage. Ratchet a real threshold up as `UNTESTED.md`'s P1/P2 tiers get covered; don't copy the sibling repos' mature P0 95/90 numbers verbatim.

See the `testing` skill's "Read tests before changing code" and the `test-coverage` skill for detail.

## Frontend Development

When working on any frontend code, apply the relevant skills from the `frontend-standards` plugin. This includes:

- `frontend-standards:project` — Core best practices (Vue 3, TypeScript, component design)
- `frontend-standards:vue-pinia` — Pinia state management patterns
- `frontend-standards:vue3-typescript` — Vue 3 + TypeScript conventions
- `frontend-standards:vue-composable-patterns` — Composable design patterns (Thin Composables, Flexible Arguments, Options Object, Reactify…)
- `frontend-standards:vue-clean-components` — Component/template layer: controller + humble components, skinny templates, when to split, passing state
- `frontend-standards:shadcn-vue` — shadcn-vue UI component patterns
- `frontend-standards:tailwind` — Tailwind CSS patterns
- `frontend-standards:vue-router` — Vue Router conventions
- `frontend-standards:api-service-layer` — API service layer patterns
- `frontend-standards:vue-security` — SPA security: XSS/v-html, VITE_ secrets, client-trust boundary, IDOR
- `frontend-standards:vue-performance` — Reactivity cost, markRaw (editors), list virtualization, lazy imports
- `frontend-standards:linting` — ESLint conventions (vue-tsc is the authority over lint)
- `frontend-standards:testing` — Vitest & Vue Test Utils patterns
- `frontend-standards:test-coverage` — Full coverage audit + writing the missing tests
- `.claude/skills/frontend/e2e/` — Playwright E2E patterns
- `frontend-standards:weekly-coverage-check` — Lightweight scheduled drift check

**Form validation:** `vee-validate` + `@vee-validate/zod` + `zod` are installed, matching the novo-mcp blueprint's pattern. Schema-validated forms (`SubmitEntryPage.vue`, `EditEntryPage.vue`, `WorkspaceForm.vue`) use `useForm`/`toTypedSchema` + the `Form`/`FormField`/`FormItem`/`FormLabel`/`FormControl`/`FormMessage` primitives in `components/ui/form/` — schemas live in `src/schemas/`. Prefer this pattern for any new or newly-touched form rather than manual ref-based validation.

**Data tables:** `@tanstack/vue-table` is installed, matching the novo-mcp blueprint. `DocumentList.vue` and `TagsPage.vue` build their rows via `useVueTable`/`getCoreRowModel`/`getSortedRowModel` (column defs with `h()`-rendered cells) instead of a plain `v-for`, rendered through the shadcn `Table` primitives in `components/ui/table/`. Prefer this pattern for any new sortable/columnar list; simple card/badge layouts (EntryCard, ApprovedKnowledgePage, WorkspacesPage) don't need it.

**Toasts:** `vue-sonner` is installed and `<Toaster />` is mounted in `App.vue`. Transient action feedback (create/update/delete/submit success or failure) goes through `toast()`/`toast.success()`/`toast.error()` — not a local `message`/`error` ref rendered as an `Alert`. Reserve inline `Alert` (with a real lucide icon — `AlertCircle` for destructive, `AlertTriangle` for warning, `CheckCircle2` for success — never a typed unicode character) for persistent/blocking page state: no workspace selected, a list failed to load, a validation result.

**Rich text editing:** `@tiptap/vue-3` + `@tiptap/starter-kit` + `@tiptap/extension-image` + `@tiptap/extension-table` + `@tiptap/extension-placeholder` + `tiptap-markdown` are installed. `TiptapMarkdownEditor.vue` (`src/components/TiptapMarkdownEditor.vue`) is the reusable WYSIWYG editor — a single file with its own toolbar (undo/redo, headings, marks, lists, blockquote, code block, link, image, table), matching the "no separate toolbar component" convention. Content is stored and transmitted as **Markdown text**, not HTML: the `Markdown` extension from `tiptap-markdown` round-trips `editor.storage.markdown.getMarkdown()` on `onUpdate` and accepts a Markdown string directly via `content`/`setContent`, so the backend's `content: str` field and `MarkdownContent.vue`'s `renderMarkdown()` pipeline are unaffected by the editor swap. It's used as a drop-in `v-model` replacement for `Textarea` in `SubmitEntryPage.vue`/`EditEntryPage.vue`'s `MarkdownSplitEditor` write pane — prefer it for any new Markdown-backed rich-text field rather than a raw `Textarea`. The Tailwind class string used to visually match the editor to the rendered output lives in `src/utils/markdownProseClasses.ts`, shared with `MarkdownContent.vue`.

**Not installed:** `permissions` was dropped — the sibling repos' version describes a specific authorization system (`usePermission.ts`, `/api/v1/me`, a permission-key catalog) that doesn't exist here; this app has no auth or authorization at all. Add it back (copy from a sibling repo, adapted) only if the underlying feature actually gets built.

Claude Code hooks in `../.claude/settings.json` reinforce the Change Protocol across the session lifecycle:

*`SessionStart` (primes context once):*
- `prime-context.mjs` (frontend-standards plugin) — branch + ahead/behind, uncommitted count, UNTESTED.md gap count, Change-Protocol reminder.

*`PreToolUse` (can block *before* an edit):*
- `check-critical-files.sh` (frontend-standards plugin) — hard-blocks edits to the P0 file list above until you've read the whole file and can explain the change.
- `protect-sensitive.mjs` (frontend-standards plugin) — asks for confirmation before deleting a test file or editing a P0 file (`src/stores/workspace.ts`, `src/services/useAPI.ts`, `src/services/useWorkspaceService.ts`).

*`PostToolUse` (inject context *after* each edit):*
- `run-tests-after-edit.sh` (frontend-standards plugin) — runs `vitest run` after any `.ts`/`.tsx`/`.vue` edit; blocks with the failure output if it broke something.
- `inject-test-context.mjs` (frontend-standards plugin) — if the edited file has a sibling test, injects that test's contents + a directive to reconcile the change with its assertions and run it.
- `inject-skill-pointers.mjs` (frontend-standards plugin) — maps the edited file's path to the relevant skills and names them.
- `inject-lint-results.mjs` (frontend-standards plugin) — runs ESLint on the edited file and injects non-auto-fixable problems.
- `inject-e2e-context.mjs` (frontend-standards plugin) — surfaces relevant Playwright specs when editing a page/route.

*`Stop` (can block completion):*
- `run-tests-on-stop.sh` (frontend-standards plugin) — runs the full `vitest` suite if any frontend source file changed this session; blocks completion on failure.
- `enforce-verify.mjs` (frontend-standards plugin) — if the session edited `src/` and the changes are still uncommitted and no verify ran after the last edit, blocks the stop.

**The enforcement wall:**
- **`pre-push` git hook** (`../.githooks/pre-push`, wired via `git config core.hooksPath .githooks` — run `npm install` from the repo root once, or run that command directly) runs `vue-tsc --noEmit` + `eslint` + `vitest run` and blocks the push on failure. Run manually: `npm run verify`.
- **CI** should run typecheck + lint + tests on every push/PR (wire this up in the repo's CI config if not already present).
