# Phase 7 — Component-by-Component shadcn-vue Migration

**Depends on:** Phase 2 (primitives), Phase 3 (tokens), Phase 4 (layout shell), Phase 6 (services, if any component fetches data directly)
**Blocks:** Phase 8 (tests are written against the migrated components' final shape)
**Risk:** low-to-medium per component, but cumulative — do this incrementally, one component per commit/PR, not as one big-bang change

## Goal

Replace the remaining hand-rolled components with shadcn-vue primitives + Tailwind utility classes, one at a time, each independently revertable. By the end of this phase, `frontend/src/style.css` should have zero remaining consumers and can be deleted entirely.

## Migration order (low risk → high risk)

Work through these in order. Each is its own unit of work — add needed shadcn primitives, replace the component's template markup with Tailwind + shadcn components, remove the corresponding CSS rules from `frontend/src/style.css`, run `npm run typecheck` + a visual check, then move to the next.

### 1. `WorkspaceIndicator.vue`
Already touched in Phase 4 (relocated into the new header). This step is about restyling it with shadcn `Badge`/`DropdownMenu` instead of its current hand-rolled markup.
```bash
npx shadcn-vue@latest add badge dropdown-menu
```

### 2. `ApprovalBadge.vue`
Replace with shadcn `Badge`, mapping `variant` to approval status (draft/approved/archived) using the `success`/`warning`/`error`/`muted` semantic tokens established in Phase 3.

### 3. `ValidationCheckItem.vue`
Replace with an `Alert` + `Badge` combo, again using the success/warning/error semantic tokens for pass/warn/fail states.
```bash
npx shadcn-vue@latest add alert
```

### 4. `ContextHash.vue`
Likely stays mostly custom (it's a hash-display chip, not a standard shadcn pattern) — restyle with Tailwind utilities, optionally add a `Tooltip` + copy-to-clipboard button using shadcn `Tooltip`.
```bash
npx shadcn-vue@latest add tooltip
```

### 5. `SearchBar.vue`
Replace with shadcn `Input` + `Button`.

### 6. `DocumentList.vue`
Replace with shadcn `Table` (or `Card`-based list if the data doesn't warrant a full table) + `DropdownMenu` for row actions (approve/archive/delete/move).
```bash
npx shadcn-vue@latest add table
```
Do **not** reach for `@tanstack/vue-table` here unless the list genuinely needs sorting/filtering/pagination at scale — a plain shadcn `Table` is sufficient for this app's current size. Adding TanStack Table speculatively is over-engineering; only revisit if a real need emerges.

### 7. `WorkspaceForm.vue`
Replace with shadcn `Dialog` + `Input`/`Textarea`/`Button` form fields.
```bash
npx shadcn-vue@latest add dialog textarea
```
**Decision point:** only add `vee-validate` + `zod` if the form's actual validation needs (beyond basic required-field checks) genuinely warrant a validation library. Don't add these dependencies speculatively just because the reference repos have them — check the form's real complexity first.

### 8. `WorkspaceActivityPanel.vue` and `WorkspaceValidationPanel.vue`
Replace with `Card` + `ScrollArea`, reusing the `ValidationCheckItem` component migrated in step 3.
```bash
npx shadcn-vue@latest add scroll-area
```

## Final cleanup step

Once all 8 components above are migrated, grep for any remaining references to `frontend/src/style.css` class names:
```bash
grep -rn "class=" frontend/src --include="*.vue" | grep -v "components/ui"
```
Manually confirm no component still depends on a selector defined in `style.css`, then:
- Delete `frontend/src/style.css`
- Remove its `import './style.css'` line from `frontend/src/main.ts`

## Files touched

**Modified (one PR/commit per component recommended):**
- `frontend/src/components/WorkspaceIndicator.vue`
- `frontend/src/components/ApprovalBadge.vue`
- `frontend/src/components/ValidationCheckItem.vue`
- `frontend/src/components/ContextHash.vue`
- `frontend/src/components/SearchBar.vue`
- `frontend/src/components/DocumentList.vue`
- `frontend/src/components/WorkspaceForm.vue`
- `frontend/src/components/WorkspaceActivityPanel.vue`
- `frontend/src/components/WorkspaceValidationPanel.vue`

**New (shadcn primitives, added incrementally as needed):**
- `frontend/src/components/ui/{badge,dropdown-menu,alert,tooltip,table,dialog,textarea,scroll-area}/*`

**Deleted (at the end):**
- `frontend/src/style.css`

**Possibly new (only if warranted, see step 7):**
- `vee-validate` + `zod` dependencies and their usage in `WorkspaceForm.vue`

## Verification / Definition of Done (per component)

- [ ] `npm run typecheck` passes
- [ ] Visual comparison against the Phase 0 baseline screenshot for the view containing this component — confirm no layout regression (intentional visual improvements are fine and expected, just make sure nothing is *broken*)
- [ ] The component's existing behavior (clicks, form submission, state changes) still works exactly as before

## Verification / Definition of Done (end of phase)

- [ ] All 9 components migrated
- [ ] `grep -rn "style.css" frontend/src` returns zero results
- [ ] `frontend/src/style.css` deleted
- [ ] Full Phase 0 checklist re-run one final time against the fully-migrated UI
- [ ] `npm run build`, `npm run typecheck`, `npm run lint:check` all pass
