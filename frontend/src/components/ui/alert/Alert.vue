<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { cn } from '@/lib/utils'
import { alertVariants, type AlertVariants } from '.'

interface Props {
  variant?: AlertVariants['variant']
  class?: HTMLAttributes['class']
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'default',
})
</script>

<template>
  <div role="alert" :class="cn(alertVariants({ variant }), props.class)">
    <slot />
  </div>
</template>
