<script setup lang="ts">
import { computed, onBeforeUnmount, ref, useAttrs, watch } from 'vue'
import { EditorContent, useEditor } from '@tiptap/vue-3'
import type { Editor } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import TiptapImage from '@tiptap/extension-image'
import { TableKit } from '@tiptap/extension-table'
import Placeholder from '@tiptap/extension-placeholder'
import { Markdown, type MarkdownStorage } from 'tiptap-markdown'
import {
  Bold,
  Italic,
  Heading1,
  Heading2,
  Heading3,
  List,
  ListOrdered,
  Quote,
  Code,
  SquareCode,
  Minus,
  Link2,
  Unlink2,
  Image as ImageIcon,
  Table as TableIcon,
  Columns3,
  Rows3,
  Trash2,
} from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'
import { MARKDOWN_PROSE_CLASSES } from '@/utils/markdownProseClasses'

defineOptions({ inheritAttrs: false })

const props = withDefaults(
  defineProps<{
    modelValue?: string
    placeholder?: string
    mode?: 'rich' | 'markdown'
    // Element the toolbar teleports into (see MarkdownSplitEditor.vue) so it
    // can span the full width of a Split-mode layout instead of being
    // confined to this editor's own column. Falls back to rendering in
    // place when unset, so this component still works stand-alone.
    toolbarTarget?: HTMLElement | null
  }>(),
  {
    modelValue: '',
    placeholder: 'Write something…',
    mode: 'rich',
    toolbarTarget: null,
  }
)
const emit = defineEmits<{ (e: 'update:modelValue', value: string): void }>()

const attrs = useAttrs()

// tiptap-markdown doesn't augment `@tiptap/core`'s `Storage` interface with
// its `MarkdownStorage` type, so `editor.storage.markdown` is untyped —
// cast locally rather than via an ambient `declare module` augmentation,
// which destabilizes unrelated `Editor` methods under `vue-tsc -b`'s
// project-reference build mode.
function getMarkdown(instance: Editor): string {
  return (instance.storage as unknown as { markdown: MarkdownStorage }).markdown.getMarkdown()
}

// Rich-text WYSIWYG is the default, but the field's value must always
// remain plain Markdown a user can drop into and edit directly — so a
// "Markdown" mode (driven by the `mode` prop — the caller owns the toggle
// UI, e.g. alongside its Editor/Split/Preview tabs) swaps the Tiptap view
// for a plain Textarea bound to the exact same v-model, no separate
// raw-text field.
const sourceText = ref(props.modelValue)

// `id`/`aria-*` need to land on whichever field is actually visible/focusable
// (the Tiptap contenteditable via `editorProps.attributes`, or this Textarea
// via v-bind) so `getByLabel`/screen readers keep working across both modes.
const fieldAttrs = computed(() => ({
  ...(typeof attrs.id === 'string' ? { id: attrs.id } : {}),
  ...(typeof attrs['aria-label'] === 'string' ? { 'aria-label': attrs['aria-label'] } : {}),
  ...(typeof attrs['aria-describedby'] === 'string'
    ? { 'aria-describedby': attrs['aria-describedby'] as string }
    : {}),
  ...(attrs['aria-invalid'] != null ? { 'aria-invalid': String(attrs['aria-invalid']) } : {}),
}))

// Resync the view being switched *into* from the view being switched away
// from — the inactive view isn't kept live-synced on every keystroke.
watch(
  () => props.mode,
  (next) => {
    const ed = editor.value
    if (!ed) return
    if (next === 'markdown') {
      sourceText.value = getMarkdown(ed)
    } else if (sourceText.value !== getMarkdown(ed)) {
      ed.commands.setContent(sourceText.value, { emitUpdate: false })
    }
  }
)

watch(sourceText, (value) => {
  if (props.mode === 'markdown') emit('update:modelValue', value)
})

// The Vue integration only assigns `editor.value` in onMounted and doesn't
// re-render on selection/transaction changes by itself (only `onUpdate`
// triggers our own emit) — this counter is read by `isActive()` below so
// toolbar active-state highlighting stays in sync with the cursor/selection,
// not just with content changes.
const revision = ref(0)

const editor = useEditor({
  content: props.modelValue || '',
  extensions: [
    StarterKit.configure({
      link: { openOnClick: false, autolink: true, HTMLAttributes: { class: 'underline' } },
    }),
    // `inline: true` matches Markdown's own semantics (an image is inline
    // content within a paragraph) and matches what tiptap-markdown's
    // built-in image serializer expects — as a block-level sibling node its
    // serialized output isn't newline-separated from the next block.
    TiptapImage.configure({ inline: true }),
    TableKit.configure({ table: { resizable: false } }),
    Placeholder.configure({
      placeholder: props.placeholder,
      emptyEditorClass:
        'before:content-[attr(data-placeholder)] before:float-left before:text-muted-foreground before:pointer-events-none before:h-0',
    }),
    // `breaks: true` matches markdown.ts's `marked.setOptions({ breaks: true })`
    // used to render the read-only Preview pane — without it, a single
    // newline (no blank line between) is parsed as a soft wrap here but a
    // hard line break there, so the same source renders differently in the
    // WYSIWYG editor vs. the preview.
    Markdown.configure({ html: false, breaks: true }),
  ],
  editorProps: {
    // A `<label for>` only associates with "labelable" HTML elements
    // (input/textarea/select/etc.) per spec — a contenteditable div isn't
    // one, so FormLabel's `for={formItemId}` silently fails to give this
    // editor an accessible name. `fieldAttrs` (id/aria-label/etc, forwarded
    // from the caller) fixes that; see its definition above.
    attributes: {
      ...fieldAttrs.value,
      class: cn(
        // No border/rounding/focus-ring here — MarkdownSplitEditor.vue's
        // outer container owns the single shared border around both the
        // write and preview panes (VS Code-style split), so this pane must
        // render flush with no focus outline of its own.
        'min-h-96 bg-background px-3 py-2 text-sm outline-none',
        MARKDOWN_PROSE_CLASSES
      ),
    },
  },
  onTransaction: () => {
    revision.value++
  },
  onUpdate: ({ editor: ed }) => {
    emit('update:modelValue', getMarkdown(ed))
  },
})

// External changes (form reset on load, "Upload .md") only need to reach
// whichever view is actually visible — the other one is resynced lazily
// when `mode` changes (see the watcher above).
watch(
  () => props.modelValue,
  (next) => {
    const value = next ?? ''
    if (props.mode === 'markdown') {
      if (value !== sourceText.value) sourceText.value = value
      return
    }
    const ed = editor.value
    if (!ed) return
    if (value !== getMarkdown(ed)) {
      ed.commands.setContent(value, { emitUpdate: false })
    }
  }
)

onBeforeUnmount(() => {
  editor.value?.destroy()
})

function isActive(name: string, itemAttrs?: Record<string, unknown>) {
  void revision.value
  return editor.value?.isActive(name, itemAttrs) ?? false
}

const activeButtonClass = 'bg-accent text-accent-foreground'

const showLinkPanel = ref(false)
const linkUrl = ref('')

function toggleLinkPanel() {
  if (showLinkPanel.value) {
    showLinkPanel.value = false
    return
  }
  linkUrl.value = (editor.value?.getAttributes('link').href as string) || ''
  showLinkPanel.value = true
}

function applyLink() {
  const url = linkUrl.value.trim()
  const chain = editor.value?.chain().focus().extendMarkRange('link')
  if (!url) {
    chain?.unsetLink().run()
  } else {
    chain?.setLink({ href: url }).run()
  }
  showLinkPanel.value = false
  linkUrl.value = ''
}

function unsetLink() {
  editor.value?.chain().focus().unsetLink().run()
}

const showImagePanel = ref(false)
const imageUrl = ref('')
const imageAlt = ref('')

function toggleImagePanel() {
  showImagePanel.value = !showImagePanel.value
  if (!showImagePanel.value) {
    imageUrl.value = ''
    imageAlt.value = ''
  }
}

function applyImage() {
  const url = imageUrl.value.trim()
  const ed = editor.value
  if (url && ed) {
    ed.chain()
      .focus()
      .setImage({ src: url, alt: imageAlt.value.trim() || undefined })
      .run()
    // Inserting an image (an atom node) leaves a NodeSelection on the image
    // itself — the next thing the user types or inserts would replace it
    // rather than land after it. Move to a plain text cursor right after.
    ed.chain().focus().setTextSelection(ed.state.selection.to).run()
  }
  showImagePanel.value = false
  imageUrl.value = ''
  imageAlt.value = ''
}

function insertTable() {
  editor.value?.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()
}
</script>

<template>
  <div class="grid gap-2">
    <Teleport :to="toolbarTarget" :disabled="!toolbarTarget">
      <div
        v-if="mode === 'rich'"
        class="flex flex-wrap items-center gap-1 rounded-md border border-input bg-muted/40 p-1"
      >
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          title="Heading 1"
          aria-label="Heading 1"
          :class="{ [activeButtonClass]: isActive('heading', { level: 1 }) }"
          @click="editor?.chain().focus().toggleHeading({ level: 1 }).run()"
        >
          <Heading1 />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          title="Heading 2"
          aria-label="Heading 2"
          :class="{ [activeButtonClass]: isActive('heading', { level: 2 }) }"
          @click="editor?.chain().focus().toggleHeading({ level: 2 }).run()"
        >
          <Heading2 />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          title="Heading 3"
          aria-label="Heading 3"
          :class="{ [activeButtonClass]: isActive('heading', { level: 3 }) }"
          @click="editor?.chain().focus().toggleHeading({ level: 3 }).run()"
        >
          <Heading3 />
        </Button>

        <span class="mx-1 h-5 w-px bg-border" aria-hidden="true" />

        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          title="Bold"
          aria-label="Bold"
          :class="{ [activeButtonClass]: isActive('bold') }"
          @click="editor?.chain().focus().toggleBold().run()"
        >
          <Bold />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          title="Italic"
          aria-label="Italic"
          :class="{ [activeButtonClass]: isActive('italic') }"
          @click="editor?.chain().focus().toggleItalic().run()"
        >
          <Italic />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          title="Inline code"
          aria-label="Inline code"
          :class="{ [activeButtonClass]: isActive('code') }"
          @click="editor?.chain().focus().toggleCode().run()"
        >
          <Code />
        </Button>

        <span class="mx-1 h-5 w-px bg-border" aria-hidden="true" />

        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          title="Bullet list"
          aria-label="Bullet list"
          :class="{ [activeButtonClass]: isActive('bulletList') }"
          @click="editor?.chain().focus().toggleBulletList().run()"
        >
          <List />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          title="Ordered list"
          aria-label="Ordered list"
          :class="{ [activeButtonClass]: isActive('orderedList') }"
          @click="editor?.chain().focus().toggleOrderedList().run()"
        >
          <ListOrdered />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          title="Blockquote"
          aria-label="Blockquote"
          :class="{ [activeButtonClass]: isActive('blockquote') }"
          @click="editor?.chain().focus().toggleBlockquote().run()"
        >
          <Quote />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          title="Code block"
          aria-label="Code block"
          :class="{ [activeButtonClass]: isActive('codeBlock') }"
          @click="editor?.chain().focus().toggleCodeBlock().run()"
        >
          <SquareCode />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          title="Horizontal rule"
          aria-label="Horizontal rule"
          @click="editor?.chain().focus().setHorizontalRule().run()"
        >
          <Minus />
        </Button>

        <span class="mx-1 h-5 w-px bg-border" aria-hidden="true" />

        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          title="Insert link"
          aria-label="Insert link"
          :class="{ [activeButtonClass]: isActive('link') }"
          @click="toggleLinkPanel"
        >
          <Link2 />
        </Button>
        <Button
          v-if="isActive('link')"
          type="button"
          variant="ghost"
          size="icon-sm"
          title="Remove link"
          aria-label="Remove link"
          @click="unsetLink"
        >
          <Unlink2 />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          title="Image"
          aria-label="Image"
          @click="toggleImagePanel"
        >
          <ImageIcon />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          title="Insert table"
          aria-label="Insert table"
          @click="insertTable"
        >
          <TableIcon />
        </Button>

        <template v-if="isActive('table')">
          <span class="mx-1 h-5 w-px bg-border" aria-hidden="true" />
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            title="Add column after"
            aria-label="Add column after"
            @click="editor?.chain().focus().addColumnAfter().run()"
          >
            <Columns3 />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            title="Add row after"
            aria-label="Add row after"
            @click="editor?.chain().focus().addRowAfter().run()"
          >
            <Rows3 />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            title="Delete table"
            aria-label="Delete table"
            @click="editor?.chain().focus().deleteTable().run()"
          >
            <Trash2 />
          </Button>
        </template>
      </div>

      <div
        v-if="showLinkPanel"
        class="flex flex-wrap items-center gap-2 rounded-md border border-input bg-muted/40 p-2"
      >
        <Input
          v-model="linkUrl"
          type="url"
          placeholder="https://example.com"
          class="h-8 flex-1"
          @keyup.enter="applyLink"
          @keyup.esc="showLinkPanel = false"
        />
        <Button type="button" size="sm" variant="outline" @click="applyLink">Apply</Button>
      </div>
      <div
        v-if="showImagePanel"
        class="flex flex-wrap items-center gap-2 rounded-md border border-input bg-muted/40 p-2"
      >
        <Input
          v-model="imageUrl"
          type="url"
          placeholder="https://example.com/image.png"
          class="h-8 flex-1"
          @keyup.enter="applyImage"
          @keyup.esc="showImagePanel = false"
        />
        <Input
          v-model="imageAlt"
          type="text"
          placeholder="Alt text"
          class="h-8 flex-1"
          @keyup.enter="applyImage"
          @keyup.esc="showImagePanel = false"
        />
        <Button type="button" size="sm" variant="outline" @click="applyImage">Apply</Button>
      </div>
    </Teleport>

    <EditorContent v-show="mode === 'rich'" :editor="editor" />
    <Textarea
      v-if="mode === 'markdown'"
      v-model="sourceText"
      v-bind="fieldAttrs"
      class="min-h-96 rounded-none border-0 font-mono text-sm shadow-none"
    />
  </div>
</template>
