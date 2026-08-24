# AGENTS.md — conventions for ANY coding agent in this repo

Claude Code sessions get all of this automatically via the `frontend-standards`
plugin (hooks, guards, skills). This file is the bridge for **every other agent**
— Codex, Cursor, Copilot, custom codegen — which gets none of that machinery.
If you are an AI coding agent, treat this file as binding.

## Non-negotiables

- **Verify before done.** Run `npm run verify` from `frontend/` (typecheck +
  tests) and report the real result. Never claim completion on unrun
  verification; never `|| true` a gate.
- **No destructive commands.** Never run `docker volume rm` / `docker compose
  down -v` / `dropdb` / `rm -rf` / `git reset --hard` / force-push / `git clean`
  or anything data-destroying — stop and ask the human to run it themselves.
- **Guarded files.** `.claude/project.json` lists `p0Files` (auth/session-critical
  — get explicit human confirmation before editing) and `criticalFiles` (do not
  edit at all). Never edit `.claude/project.json` or `.claude/settings*.json`
  yourself. When you CREATE a file carrying auth/session/token/permission logic,
  tell the human it belongs in those lists.
- **Tests are real.** Read the sibling `.test.ts` before changing source; update
  it in the same change when you deliberately change a contract. A test must
  import its actual subject — never reimplement logic inside a test, never mock
  the module under test wholesale.

## Code conventions (the law, not suggestions)

Full canon: `https://github.com/Luminar-Consulting-Org/metamorphic-claude-conventions`
→ `plugins/frontend-standards/skills/frontend/*/SKILL.md`. Read `page-patterns`
(page composition), `project`, and `vue3-typescript` before generating code;
per-domain skills (`api-service-layer`, `vee-validate`, `vue-pinia`,
`vue-security`, `testing`) as relevant. The essentials:

- Icons: `lucide-vue-next` only. Height before width (`h-4 w-4`).
- Colors: semantic tokens only (`bg-success-muted`, `text-error`) — no raw hex,
  no `bg-green-100`-style palette-for-meaning. ESLint enforces this.
- Pages: `pages/<feature>/Index.vue`, one `space-y-6` wrapper, `PageHeader`
  component first, all four data states (loading = `Skeleton`, error box, dashed
  empty state, loaded). Grouped surfaces sit on `bg-muted`.
- Data: component → composable → service → `useApi()`. Fetch in `onMounted`.
- Forms: vee-validate + yup. Tables: `@tanstack/vue-table`. Toasts: `vue-sonner`
  direct import, one `<Toaster position="bottom-right">`.
- Breadcrumbs: every crumb links except the last. Destructive confirms:
  `AlertDialog`, never `window.confirm`.
- E2E specifics live in this repo at `.claude/skills/frontend/e2e/SKILL.md`.

## Validation

Generated/edited code must pass `npx eslint` (the shared
`eslint-frontend-standards.mjs` rules are wired into this repo's config) and
`npm run verify` before it is presented as done.

---

*Synced from metamorphic-claude-conventions `plugins/frontend-standards/templates/AGENTS.md` — do not hand-edit; change the template upstream.*
