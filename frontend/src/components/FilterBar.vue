<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useTagService } from '@/services/useTagService'
import {
  FILTER_COMPONENTS,
  FILTER_STATUSES,
  FILTER_TYPES,
  UNSET_OPTION,
} from '@/constants/entryOptions'
import type { Tag } from '@/types/entry'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

withDefaults(
  defineProps<{
    type?: string
    component?: string
    status?: string
    tag?: string
    showLimit?: boolean
    limit?: number
  }>(),
  {
    type: '',
    component: '',
    status: '',
    tag: '',
    showLimit: false,
    limit: 10,
  }
)

const emit = defineEmits<{
  'update:type': [value: string]
  'update:component': [value: string]
  'update:status': [value: string]
  'update:tag': [value: string]
  'update:limit': [value: number]
}>()

const { listTags } = useTagService()
const catalogTags = ref<Tag[]>([])

onMounted(async () => {
  const { tags } = await listTags()
  catalogTags.value = tags
})

// Reka UI's Select forbids an empty-string SelectItem value, so the "any/all"
// options render with UNSET_OPTION and get translated back to '' here.
function unwrap(value: unknown): string {
  const v = String(value ?? '')
  return v === UNSET_OPTION ? '' : v
}
</script>

<template>
  <div class="flex flex-wrap items-end gap-3">
    <div class="grid gap-1.5">
      <Label for="filter-type">Type</Label>
      <Select
        :model-value="type || UNSET_OPTION"
        @update:model-value="(v) => emit('update:type', unwrap(v))"
      >
        <SelectTrigger id="filter-type" size="sm" class="w-40"><SelectValue /></SelectTrigger>
        <SelectContent>
          <SelectItem v-for="o in FILTER_TYPES" :key="o.value" :value="o.value">{{
            o.label
          }}</SelectItem>
        </SelectContent>
      </Select>
    </div>
    <div class="grid gap-1.5">
      <Label for="filter-component">Component</Label>
      <Select
        :model-value="component || UNSET_OPTION"
        @update:model-value="(v) => emit('update:component', unwrap(v))"
      >
        <SelectTrigger id="filter-component" size="sm" class="w-40"><SelectValue /></SelectTrigger>
        <SelectContent>
          <SelectItem v-for="o in FILTER_COMPONENTS" :key="o.value" :value="o.value">{{
            o.label
          }}</SelectItem>
        </SelectContent>
      </Select>
    </div>
    <div class="grid gap-1.5">
      <Label for="filter-status">Status</Label>
      <Select
        :model-value="status || UNSET_OPTION"
        @update:model-value="(v) => emit('update:status', unwrap(v))"
      >
        <SelectTrigger id="filter-status" size="sm" class="w-40"><SelectValue /></SelectTrigger>
        <SelectContent>
          <SelectItem v-for="o in FILTER_STATUSES" :key="o.value" :value="o.value">{{
            o.label
          }}</SelectItem>
        </SelectContent>
      </Select>
    </div>
    <div class="grid gap-1.5">
      <Label for="filter-tag">Tag</Label>
      <Select
        :model-value="tag || UNSET_OPTION"
        @update:model-value="(v) => emit('update:tag', unwrap(v))"
      >
        <SelectTrigger id="filter-tag" size="sm" class="w-40"><SelectValue /></SelectTrigger>
        <SelectContent>
          <SelectItem :value="UNSET_OPTION">All tags</SelectItem>
          <SelectItem v-for="t in catalogTags" :key="t.id" :value="t.name">{{ t.name }}</SelectItem>
        </SelectContent>
      </Select>
    </div>
    <div v-if="showLimit" class="grid gap-1.5">
      <Label for="filter-limit">Limit</Label>
      <Select
        :model-value="String(limit)"
        @update:model-value="(v) => emit('update:limit', Number(v))"
      >
        <SelectTrigger id="filter-limit" size="sm" class="w-20"><SelectValue /></SelectTrigger>
        <SelectContent>
          <SelectItem value="5">5</SelectItem>
          <SelectItem value="10">10</SelectItem>
          <SelectItem value="20">20</SelectItem>
          <SelectItem value="50">50</SelectItem>
        </SelectContent>
      </Select>
    </div>
  </div>
</template>
