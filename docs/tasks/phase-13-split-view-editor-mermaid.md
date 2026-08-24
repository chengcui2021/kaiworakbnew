# Phase 13 — Split-View Editor & Mermaid Rendering

**Depends on:** Phase 12 (the shared `MarkdownEditorTabs.vue` extraction — already merged; this phase replaces its tab toggle with a true split view)
**Blocks:** none
**Risk:** medium — touches a component shared by both entry-authoring pages, adds a new runtime dependency, and changes how sanitization and rendering interact

## Origin

New feature request (JIRA), not part of the UX review remediation arc: "Split-View Editor: Replace the current single-pane textarea with a VS Code-style split view: raw Markdown editor on the left, live rendered preview on the right." Plus: "Mermaid Support: Integrate mermaid.js ... into the preview pane to automatically render Mermaid diagrams defined in the Markdown."

## Current state

- `frontend/src/components/MarkdownEditorTabs.vue` renders a shadcn `Tabs` toggle (`write` | `preview`) — only one pane visible at a time. Consumed by `frontend/src/pages/SubmitEntryPage.vue:169-208` and `frontend/src/pages/EditEntryPage.vue:208-216`.
- `frontend/src/components/MarkdownContent.vue` renders preview HTML via `computed(() => renderMarkdown(props.source))` and `v-html`.
- `frontend/src/utils/markdown.ts` renders with `marked` (`^18.0.5`, `{ gfm: true, breaks: true }`) then sanitizes with `DOMPurify`.
- No mermaid or diagram-rendering dependency exists anywhere in `frontend/package.json` today — this is a net-new dependency.
- `frontend/e2e/markdown-editor-tabs.spec.ts` already covers the current tab-toggle behavior and will need updating once the toggle becomes a split view.

## Goal

Replace the write/preview tab toggle with a side-by-side split view on wide viewports (raw editor left, live-rendered preview right, both visible and in sync as the user types), and render `​```mermaid` fenced code blocks in the preview as diagrams instead of raw code.

## Work items

### 1. Split-view layout

**Files:** `frontend/src/components/MarkdownEditorTabs.vue`

Add a `split` mode alongside `write`/`preview`. Recommended approach: keep the existing `Tabs` toggle for narrow viewports (where side-by-side isn't usable), and add a `grid grid-cols-2 gap-4` layout for `md:`+ viewports showing the `write` and `preview` slots simultaneously, always live (no explicit "Preview" click needed). This mirrors the existing responsive-collapse pattern already used elsewhere in the app rather than introducing a new one. Rename the component if its scope changes enough to warrant it (e.g. `MarkdownSplitEditor.vue`) — a mechanical rename across `SubmitEntryPage.vue`/`EditEntryPage.vue` either way.

### 2. Live re-render performance

**Files:** `frontend/src/components/MarkdownContent.vue`

Today's preview only (re-)renders when the user clicks into the preview tab. In split view it re-renders on every keystroke. Debounce the `renderMarkdown` call (e.g. 150-250ms) so large entries don't re-parse Markdown and re-run mermaid on every character.

### 3. Mermaid dependency & rendering

**Files:** `frontend/package.json`, `frontend/src/utils/markdown.ts`, `frontend/src/components/MarkdownContent.vue`

- Add `mermaid` as a dependency; dynamically `import('mermaid')` inside `MarkdownContent.vue` rather than a static top-level import, since it's only needed where previews render and is a non-trivial bundle addition.
- Extend the `marked` renderer so a fenced code block tagged `mermaid` emits a placeholder element (e.g. `<pre class="mermaid" data-mermaid-src="...">`) instead of a normal `<pre><code>` block.
- `v-html` content isn't reactive to Vue lifecycle hooks, so mermaid's `run()` (which scans for `.mermaid` elements and replaces them with rendered SVG) must be triggered manually in a `watch` on the computed HTML, after `nextTick()`.
- **Sanitization ordering matters:** `DOMPurify` runs on the full `marked()` output. Raw mermaid source often contains characters (`<`, `>`, quotes) that DOMPurify may strip if placed as element text content. Store the raw mermaid source in a `data-*` attribute (URI- or base64-encoded) rather than as element text, and configure the `DOMPurify` allowlist to permit that specific class/attribute — verify this doesn't loosen sanitization for anything else rendered through the same pipeline.
- Invalid mermaid syntax should render an inline error state scoped to that one diagram, not throw and blank the whole preview pane.

### 4. Apply to both consumers

**Files:** `frontend/src/pages/SubmitEntryPage.vue`, `frontend/src/pages/EditEntryPage.vue`

Both already consume the shared component via slots — confirm both render correctly in split mode with no page-specific breakage (Submit's file-upload flow currently force-switches `contentMode` to `'preview'` after a file loads; decide what that should do once "preview" isn't a distinct mode from "split").

## Files touched

**New:**
- `mermaid` npm dependency

**Modified:**
- `frontend/src/components/MarkdownEditorTabs.vue`
- `frontend/src/components/MarkdownContent.vue`
- `frontend/src/utils/markdown.ts`
- `frontend/src/pages/SubmitEntryPage.vue`
- `frontend/src/pages/EditEntryPage.vue`
- `frontend/e2e/markdown-editor-tabs.spec.ts`

## Verification / Definition of Done

- [x] `npx vue-tsc --noEmit` passes
- [x] `npx eslint .` passes
- [x] Visual check: split view shows editor + live preview side-by-side on desktop widths, collapses to a usable single-pane toggle on mobile widths
- [x] Manual check: typing in the editor updates the preview without noticeable lag on a ~2000-word entry
- [x] Manual check: a fenced `​```mermaid` block with a valid flowchart renders as an SVG diagram in the preview
- [x] Manual check: a fenced `​```mermaid` block with invalid syntax shows a scoped inline error, not a blank/broken preview
- [x] Security check: confirm the mermaid-source sanitization path doesn't reintroduce an XSS vector (test with a mermaid block containing `<script>`/`onerror=` payloads in node labels)
- [x] `npm run test:unit` passes
- [x] `npm run test:e2e` passes (replaced `markdown-editor-tabs.spec.ts` with `markdown-split-editor.spec.ts` for the new split-view interaction model)
- [x] `UNTESTED.md` updated
- [x] `npm run verify` passes
- [x] Update `docs/tasks/00-index.md`: check off Phase 13 once merged and verified

## Follow-up: Editor/Split/Preview mode switch

Shipped as an immediate follow-up (same session): the viewport-driven collapse described above (auto-split on desktop, tab toggle on mobile) was replaced with an explicit, viewport-independent 3-way mode switch — `Editor` / `Split` / `Preview` tabs, defaulting to `Split`, available at every screen width. Users on any device can now pick a focused single-pane view or the side-by-side split. `MarkdownSplitEditor.vue` no longer uses `TabsContent`/`forceMount` for this (a 3-state value doesn't map onto TabsContent's single-active-panel model) — panes are plain `v-show`'d divs driven off `modelValue` directly. A separate `MarkdownEditorTabs.vue`-adjacent TipTap WYSIWYG option was researched (via Context7) and explicitly deferred — see the CLAUDE.md note on `tiptap-editor` not being installed in this app; that remains a bigger, separately-scoped decision.
