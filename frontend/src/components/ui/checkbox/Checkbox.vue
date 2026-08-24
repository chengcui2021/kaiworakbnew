<script setup lang="ts">
import type { CheckboxRootProps } from 'reka-ui'
import type { HTMLAttributes } from 'vue'
import { computed } from 'vue'
import { reactiveOmit } from '@vueuse/core'
import { Check } from 'lucide-vue-next'
import { CheckboxIndicator, CheckboxRoot, useForwardPropsEmits } from 'reka-ui'
import { cn } from '@/lib/utils'

/**
 * Backwards-compatible wrapper:
 * - Supports reka-ui: modelValue / update:modelValue
 * - ALSO supports legacy: checked / update:checked
 */
type Props = CheckboxRootProps & {
  class?: HTMLAttributes['class']
  checked?: boolean // legacy support
}

const props = defineProps<Props>()

const emits = defineEmits<{
  'update:modelValue': [value: boolean | 'indeterminate']
  'update:checked': [value: boolean]
}>()

// Forward everything except class / checked / modelValue
const delegatedProps = reactiveOmit(props, 'class', 'checked', 'modelValue')
const forwarded = useForwardPropsEmits(delegatedProps, emits)

// Determine effective value:
// - modelValue wins
// - fallback to checked (legacy)
const effectiveModelValue = computed(() => {
  if (props.modelValue !== undefined) return props.modelValue
  return props.checked
})

function onUpdateModelValue(v: boolean | 'indeterminate') {
  const boolVal = v === true

  // Emit both APIs
  emits('update:modelValue', v)
  emits('update:checked', boolVal)
}
</script>

<template>
  <CheckboxRoot
    data-slot="checkbox"
    v-bind="forwarded"
    :model-value="effectiveModelValue"
    @update:model-value="onUpdateModelValue"
    :class="
      cn(
        'peer border-input data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground data-[state=checked]:border-primary focus-visible:border-ring focus-visible:ring-ring/50 aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive size-4 shrink-0 rounded-[4px] border shadow-xs transition-shadow outline-none focus-visible:ring-[3px] disabled:cursor-not-allowed disabled:opacity-50',
        props.class
      )
    "
  >
    <CheckboxIndicator
      data-slot="checkbox-indicator"
      class="flex items-center justify-center text-current transition-none"
    >
      <slot>
        <Check class="size-3.5" />
      </slot>
    </CheckboxIndicator>
  </CheckboxRoot>
</template>
