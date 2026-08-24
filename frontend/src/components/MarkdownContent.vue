<script setup lang="ts">
import { computed, onMounted, ref, toRef, watch } from 'vue'
import { refDebounced } from '@vueuse/core'
import { renderMarkdown } from '@/utils/markdown'
import { renderMermaidDiagrams } from '@/utils/mermaidRender'
import { MARKDOWN_PROSE_CLASSES } from '@/utils/markdownProseClasses'

const props = defineProps<{
  source?: string
  clamped?: boolean
}>()

const debouncedSource = refDebounced(toRef(props, 'source'), 200)
const html = computed(() => renderMarkdown(debouncedSource.value))
const rootEl = ref<HTMLElement | null>(null)

// `watch` with `immediate: true` fires synchronously during setup, before
// this component's first mount — rootEl wouldn't be set yet. onMounted
// covers the initial render; the (non-immediate) watch covers later edits,
// each of which only fires once the component is already mounted, so
// flush: 'post' correctly defers it until after the DOM update lands.
onMounted(() => {
  if (rootEl.value) {
    void renderMermaidDiagrams(rootEl.value)
  }
})

watch(
  html,
  () => {
    if (rootEl.value) {
      void renderMermaidDiagrams(rootEl.value)
    }
  },
  { flush: 'post' }
)
</script>

<template>
  <div
    v-if="html"
    ref="rootEl"
    class="text-sm leading-relaxed"
    :class="[MARKDOWN_PROSE_CLASSES, { 'line-clamp-4': clamped }]"
    v-html="html"
  />
  <p v-else class="text-sm text-muted-foreground">—</p>
</template>
