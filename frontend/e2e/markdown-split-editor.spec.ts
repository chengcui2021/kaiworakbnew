import { test, expect } from '@playwright/test'
import { mockApi } from './support/mockApi'

/**
 * Covers Phase 13 + its follow-up UX pass: the shared MarkdownSplitEditor
 * component used by both Submit Entry and Edit Entry. It defaults to Split
 * mode (raw editor + live rendered preview both visible, no click needed)
 * and offers an explicit Editor/Split/Preview switch — real ARIA tabs, not
 * viewport-dependent — so users can also view just the raw source or just
 * the rendered output.
 *
 * The write pane is `TiptapMarkdownEditor.vue`, a WYSIWYG editor that still
 * round-trips plain Markdown text (via `tiptap-markdown`). Content is driven
 * through real keystrokes (`page.keyboard.type`), not `.fill()` — Tiptap's
 * Markdown input rules (`# ` -> heading, `> ` -> blockquote, backtick fence
 * -> code block) only fire on real typed input, and `.fill()` on a
 * contenteditable bypasses ProseMirror's transaction/input-rule pipeline
 * entirely. Table and image content have no typed-markdown-syntax input
 * rule once real Table/Image extensions are registered, so those are driven
 * via the toolbar instead. The Preview pane itself is untouched by any of
 * this — it still renders whatever Markdown the editor currently holds.
 */
test.describe('Markdown split editor', () => {
  test.beforeEach(async ({ page }) => {
    await mockApi(page)
  })

  test('Submit Entry: defaults to Split mode with editor and preview both visible', async ({
    page,
  }) => {
    await page.goto('/submit')

    await expect(page.getByRole('tab', { name: 'Split' })).toHaveAttribute('aria-selected', 'true')
    const preview = page.locator('[data-test="markdown-preview-pane"]')
    const content = page.getByLabel('Content', { exact: true })
    await expect(content).toBeVisible()
    await expect(preview).toBeVisible()

    await content.click()
    await page.keyboard.type('# Hello world')

    await expect(preview.getByRole('heading', { name: 'Hello world' })).toBeVisible()
  })

  test('Edit Entry: defaults to Split mode with editor and preview both visible', async ({
    page,
  }) => {
    await page.goto('/entries/entry-1/edit')

    const preview = page.locator('[data-test="markdown-preview-pane"]')
    await expect(page.getByLabel('Content', { exact: true })).toBeVisible()
    await expect(preview.getByText('Seeded for e2e smoke tests')).toBeVisible()
  })

  test('Editor/Split/Preview tabs toggle which pane(s) are visible', async ({ page }) => {
    await page.goto('/submit')

    const editorTab = page.getByRole('tab', { name: 'Editor' })
    const splitTab = page.getByRole('tab', { name: 'Split' })
    const previewTab = page.getByRole('tab', { name: 'Preview' })
    const writePane = page.locator('[data-test="markdown-write-pane"]')
    const previewPane = page.locator('[data-test="markdown-preview-pane"]')

    // Split (default): both panes visible.
    await expect(splitTab).toHaveAttribute('aria-selected', 'true')
    await expect(writePane).toBeVisible()
    await expect(previewPane).toBeVisible()

    // Editor: only the write pane.
    await editorTab.click()
    await expect(editorTab).toHaveAttribute('aria-selected', 'true')
    await expect(splitTab).toHaveAttribute('aria-selected', 'false')
    await expect(writePane).toBeVisible()
    await expect(previewPane).toBeHidden()

    // Preview: only the rendered pane.
    await previewTab.click()
    await expect(previewTab).toHaveAttribute('aria-selected', 'true')
    await expect(writePane).toBeHidden()
    await expect(previewPane).toBeVisible()

    // Back to Split: both visible again.
    await splitTab.click()
    await expect(writePane).toBeVisible()
    await expect(previewPane).toBeVisible()
  })

  test('Submit Entry: table, blockquote, and image render with styling in preview', async ({
    page,
  }) => {
    await page.goto('/submit')

    const content = page.getByLabel('Content', { exact: true })
    const writePane = page.locator('[data-test="markdown-write-pane"]')
    const preview = page.locator('[data-test="markdown-preview-pane"]')

    // Blockquote via the "> " input rule, then two Enters to lift back out
    // to a plain paragraph before inserting the image.
    await content.click()
    await page.keyboard.type('> A quoted note from the meeting.')
    await page.keyboard.press('Enter')
    await page.keyboard.press('Enter')

    // Image via the toolbar (no typed-markdown-syntax input rule once a
    // real Image extension is registered).
    await page.getByRole('button', { name: 'Image', exact: true }).click()
    await page
      .getByPlaceholder('https://example.com/image.png')
      .fill('https://example.com/diagram.png')
    await page.getByPlaceholder('Alt text').fill('diagram')
    await page.getByRole('button', { name: 'Apply' }).click()

    // Table via the toolbar, inserted last so there's no need to move the
    // cursor past it afterwards. Default insert is 3x3 with a header row;
    // only the first column of the header and first body row is filled —
    // enough to exercise real table markup end to end. Click the first
    // header cell explicitly rather than typing immediately after the
    // toolbar click — the freshly inserted table's first cell isn't
    // reliably focused in the same tick the button click resolves.
    await page.getByRole('button', { name: 'Insert table', exact: true }).click()
    await writePane.locator('th').first().click()
    await page.keyboard.type('Component')
    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')
    await page.keyboard.type('api')

    await expect(preview.locator('blockquote')).toHaveText('A quoted note from the meeting.')
    await expect(preview.locator('table')).toBeVisible()
    await expect(preview.locator('th', { hasText: 'Component' })).toBeVisible()
    await expect(preview.locator('td', { hasText: 'api' })).toBeVisible()
    await expect(preview.locator('img[alt="diagram"]')).toHaveAttribute(
      'src',
      'https://example.com/diagram.png'
    )
  })

  test('Submit Entry: a valid mermaid diagram renders as an SVG in the preview', async ({
    page,
  }) => {
    await page.goto('/submit')

    const content = page.getByLabel('Content', { exact: true })
    await content.click()
    await page.keyboard.type('# Flow')
    await page.keyboard.press('Enter')
    await page.keyboard.type('```mermaid')
    await page.keyboard.press('Enter')
    await page.keyboard.type('graph TD;')
    await page.keyboard.press('Enter')
    await page.keyboard.type('  A-->B;')

    const preview = page.locator('[data-test="markdown-preview-pane"]')
    await expect(preview.getByRole('heading', { name: 'Flow' })).toBeVisible()
    await expect(preview.locator('.mermaid-rendered svg')).toBeVisible()
  })

  test('Submit Entry: invalid mermaid syntax shows a scoped error without blanking the preview', async ({
    page,
  }) => {
    await page.goto('/submit')

    const content = page.getByLabel('Content', { exact: true })
    await content.click()
    await page.keyboard.type('# Flow')
    await page.keyboard.press('Enter')
    await page.keyboard.type('```mermaid')
    await page.keyboard.press('Enter')
    await page.keyboard.type('this is not valid mermaid syntax')

    const preview = page.locator('[data-test="markdown-preview-pane"]')
    await expect(preview.getByRole('heading', { name: 'Flow' })).toBeVisible()
    await expect(preview.getByText('Invalid Mermaid diagram')).toBeVisible()
    await expect(preview.locator('.mermaid-rendered svg')).toHaveCount(0)
  })

  test('Submit Entry: choosing a template hydrates empty content with no confirmation', async ({
    page,
  }) => {
    await page.goto('/submit')

    const preview = page.locator('[data-test="markdown-preview-pane"]')
    await page.getByLabel('Start from a template').click()
    await page.getByRole('option', { name: 'Meeting Minutes' }).click()

    await expect(page.getByRole('alertdialog')).toHaveCount(0)
    await expect(
      preview.getByRole('heading', { name: 'Meeting Minutes: [Meeting Title]' })
    ).toBeVisible()
  })

  test('Submit Entry: choosing a template over existing content asks for confirmation', async ({
    page,
  }) => {
    await page.goto('/submit')

    const content = page.getByLabel('Content', { exact: true })
    const preview = page.locator('[data-test="markdown-preview-pane"]')
    await content.click()
    await page.keyboard.type('# My draft notes')

    await page.getByLabel('Start from a template').click()
    await page.getByRole('option', { name: 'Meeting Minutes' }).click()

    const dialog = page.getByRole('alertdialog')
    await expect(dialog).toBeVisible()
    await expect(dialog).toContainText('Meeting Minutes')

    // Cancel: original content survives untouched.
    await dialog.getByRole('button', { name: 'Cancel' }).click()
    await expect(dialog).toBeHidden()
    await expect(preview.getByRole('heading', { name: 'My draft notes' })).toBeVisible()

    // Confirm: template replaces the draft content.
    await page.getByLabel('Start from a template').click()
    await page.getByRole('option', { name: 'Meeting Minutes' }).click()
    await page.getByRole('alertdialog').getByRole('button', { name: 'Load template' }).click()

    await expect(
      preview.getByRole('heading', { name: 'Meeting Minutes: [Meeting Title]' })
    ).toBeVisible()
    await expect(preview.getByRole('heading', { name: 'My draft notes' })).toHaveCount(0)
  })
})
