<script setup lang="ts">
import { computed, ref } from 'vue'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'

const props = withDefaults(
  defineProps<{ modelValue: 'write' | 'split' | 'preview'; label?: string }>(),
  { label: 'Content editor mode' }
)
const emit = defineEmits<{
  (e: 'update:modelValue', value: 'write' | 'split' | 'preview'): void
}>()

// A 3-way mode doesn't map onto TabsContent's single-active-panel model (in
// 'split' neither 'write' nor 'preview' "is" the active tab, both are), so
// panes are plain v-show'd divs driven off modelValue directly rather than
// TabsContent's own data-state.
const showWrite = computed(() => props.modelValue !== 'preview')
const showPreview = computed(() => props.modelValue !== 'write')

// TiptapMarkdownEditor's formatting toolbar lives inside the write pane, so
// in Split mode it's confined to that pane's column — pushing the editor's
// bordered content box down while the preview pane's box starts flush at
// the top, leaving the two panes visibly unlevel. Handing the write slot a
// teleport target here lets the toolbar render in this full-width row
// instead (still defined entirely inside TiptapMarkdownEditor.vue, per the
// "single file, own toolbar" convention — only its DOM output relocates),
// so both panes' content boxes start at the same row underneath it.
const toolbarSlot = ref<HTMLDivElement | null>(null)
</script>

<template>
  <Tabs
    :model-value="modelValue"
    class="grid gap-2"
    @update:model-value="(v) => emit('update:modelValue', v as 'write' | 'split' | 'preview')"
  >
    <div class="flex flex-wrap items-center gap-4">
      <TabsList class="w-fit" :aria-label="label">
        <TabsTrigger value="split">Split</TabsTrigger>
        <TabsTrigger value="write">Editor</TabsTrigger>
        <TabsTrigger value="preview">Preview</TabsTrigger>
      </TabsList>
      <div v-if="$slots.actions" class="flex items-center gap-2">
        <slot name="actions" />
      </div>
    </div>
    <div v-show="showWrite" ref="toolbarSlot" class="grid gap-2" />
    <div
      class="grid divide-y divide-input overflow-hidden rounded-md border border-input"
      :class="{ 'md:grid-cols-2 md:divide-x md:divide-y-0': modelValue === 'split' }"
    >
      <div v-show="showWrite" class="bg-background" data-test="markdown-write-pane">
        <slot name="write" :toolbar-target="toolbarSlot" />
      </div>
      <div v-show="showPreview" class="min-h-96 bg-card" data-test="markdown-preview-pane">
        <slot name="preview" />
      </div>
    </div>
  </Tabs>
</template>
