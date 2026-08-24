<script setup lang="ts">
import type { TabsListProps } from 'reka-ui'
import { TabsList } from 'reka-ui'
import { cn } from '@/lib/utils'

const props = withDefaults(defineProps<TabsListProps & { class?: string }>(), {
  class: '',
})
</script>

<template>
  <TabsList
    data-slot="tabs-list"
    :class="
      cn(
        'inline-flex h-10 items-center justify-center rounded-md bg-muted p-1 text-muted-foreground',
        props.class
      )
    "
    v-bind="{ loop: props.loop }"
  >
    <slot />
  </TabsList>
</template>
