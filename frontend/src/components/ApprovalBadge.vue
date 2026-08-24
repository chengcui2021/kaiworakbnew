<script setup lang="ts">
import { computed, type Component } from 'vue'
import { Archive, CheckCircle2, Circle, FileEdit } from 'lucide-vue-next'
import { Badge } from '@/components/ui/badge'

const props = defineProps<{ status: string }>()

const META: Record<string, { label: string; icon: Component; class: string }> = {
  draft: {
    label: 'Draft',
    icon: FileEdit,
    class: 'border-transparent bg-warning text-warning-foreground',
  },
  approved: {
    label: 'Approved',
    icon: CheckCircle2,
    class: 'border-transparent bg-success text-success-foreground',
  },
  archived: {
    label: 'Archived',
    icon: Archive,
    class: 'border-transparent bg-muted text-muted-foreground',
  },
}

const meta = computed(
  () => META[props.status] || { label: props.status, icon: Circle, class: 'border-transparent' }
)
</script>

<template>
  <Badge :class="meta.class" :data-test="`approval-badge-${status}`">
    <component :is="meta.icon" class="size-3" aria-hidden="true" />
    {{ meta.label }}
  </Badge>
</template>
