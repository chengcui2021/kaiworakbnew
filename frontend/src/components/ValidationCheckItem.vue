<script setup lang="ts">
import { computed } from 'vue'
import { AlertTriangle, CheckCircle2, XCircle } from 'lucide-vue-next'
import type { ValidationCheck } from '../types/domain'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'

const props = defineProps<{ check: ValidationCheck }>()

const icon = computed(() => {
  if (props.check.status === 'pass') return CheckCircle2
  if (props.check.status === 'fail') return XCircle
  return AlertTriangle
})

const variant = computed<'success' | 'destructive' | 'warning'>(() => {
  if (props.check.status === 'pass') return 'success'
  if (props.check.status === 'fail') return 'destructive'
  return 'warning'
})
</script>

<template>
  <li :data-test="`check-${check.name}`">
    <Alert :variant="variant">
      <component :is="icon" class="size-4" aria-hidden="true" />
      <AlertTitle class="flex items-center justify-between gap-2">
        {{ check.label }}
        <Badge variant="outline">{{ check.status }}</Badge>
      </AlertTitle>
      <AlertDescription>{{ check.message }}</AlertDescription>
    </Alert>
  </li>
</template>
