<script setup lang="ts">
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'

const props = withDefaults(
  defineProps<{ disabled?: boolean; placeholder?: string; modelValue?: string }>(),
  { modelValue: '' }
)
const emit = defineEmits<{
  (e: 'search', query: string): void
  (e: 'update:modelValue', value: string): void
}>()

function submit() {
  if (props.disabled) return
  emit('search', props.modelValue)
}
</script>

<template>
  <form class="flex gap-2" @submit.prevent="submit">
    <Input
      :model-value="modelValue"
      type="search"
      :disabled="disabled"
      :placeholder="placeholder || 'Search documents in this workspace…'"
      data-test="search-input"
      @update:model-value="(v) => emit('update:modelValue', String(v ?? ''))"
    />
    <Button type="submit" :disabled="disabled" data-test="search-submit">Search</Button>
  </form>
</template>
