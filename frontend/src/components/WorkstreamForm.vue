<script setup lang="ts">
import { watch } from 'vue'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import type { Workstream } from '../types/domain'
import { workstreamSchema, type WorkstreamFormValues } from '@/schemas/workstreamSchema'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

const props = defineProps<{
  open: boolean
  workstream?: Workstream | null
  submitLabel?: string
}>()
const emit = defineEmits<{
  (e: 'update:open', value: boolean): void
  (e: 'submit', payload: { name: string; description: string }): void
}>()

const { handleSubmit, resetForm } = useForm<WorkstreamFormValues>({
  validationSchema: toTypedSchema(workstreamSchema),
  initialValues: { name: '', description: '' },
})

watch(
  () => props.open,
  (open) => {
    if (open) {
      resetForm({
        values: {
          name: props.workstream?.name || '',
          description: props.workstream?.description || '',
        },
      })
    }
  },
  { immediate: true }
)

const onSubmit = handleSubmit((values) => {
  emit('submit', { name: values.name.trim(), description: (values.description || '').trim() })
})
</script>

<template>
  <Dialog :open="open" @update:open="emit('update:open', $event)">
    <DialogContent>
      <DialogHeader>
        <DialogTitle>{{
          workstream ? `Edit "${workstream.name}"` : 'Create workstream'
        }}</DialogTitle>
      </DialogHeader>
      <form class="grid gap-4" @submit="onSubmit">
        <FormField v-slot="{ componentField }" name="name">
          <FormItem>
            <FormLabel>Name</FormLabel>
            <FormControl>
              <Input placeholder="e.g. Marketing Q1" data-test="ws-name" v-bind="componentField" />
            </FormControl>
            <FormMessage />
          </FormItem>
        </FormField>
        <FormField v-slot="{ componentField }" name="description">
          <FormItem>
            <FormLabel>Description</FormLabel>
            <FormControl>
              <Textarea
                placeholder="Optional description"
                data-test="ws-description"
                v-bind="componentField"
              />
            </FormControl>
            <FormMessage />
          </FormItem>
        </FormField>
        <DialogFooter>
          <Button type="submit" data-test="ws-submit">{{ submitLabel || 'Save' }}</Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
</template>
