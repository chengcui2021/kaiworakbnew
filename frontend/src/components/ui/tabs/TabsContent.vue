<script setup lang="ts">
import type { TabsContentProps } from 'reka-ui'
import { TabsContent } from 'reka-ui'
import { cn } from '@/lib/utils'

const props = withDefaults(defineProps<TabsContentProps & { class?: string }>(), {
  class: '',
})
</script>

<template>
  <TabsContent
    data-slot="tabs-content"
    :class="
      cn(
        'mt-2 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
        props.class
      )
    "
    :value="props.value"
    :force-mount="props.forceMount"
  >
    <slot />
  </TabsContent>
</template>
