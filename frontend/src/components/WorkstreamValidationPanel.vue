<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { AlertCircle } from 'lucide-vue-next'
import { useWorkstreamService } from '../services/useWorkstreamService'
import { formatDate } from '../utils/format'
import type { WorkstreamValidationResult } from '../types/domain'
import ValidationCheckItem from './ValidationCheckItem.vue'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'

const props = defineProps<{ workstreamId: string }>()

const { validateWorkstream } = useWorkstreamService()

const result = ref<WorkstreamValidationResult | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

async function runValidation() {
  loading.value = true
  error.value = null
  try {
    result.value = await validateWorkstream(props.workstreamId)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Validation failed'
    result.value = null
  } finally {
    loading.value = false
  }
}

function statusText(status: string) {
  if (status === 'pass') return 'All checks passed'
  if (status === 'fail') return 'Validation failed'
  return 'Validation warnings'
}

function formatTimestamp(value: string) {
  const d = new Date(value)
  return `${formatDate(value)} ${d.toLocaleTimeString('en-GB')}`
}

const OVERALL_CLASS: Record<string, string> = {
  pass: 'border-transparent bg-success text-success-foreground',
  fail: 'border-transparent bg-destructive text-white',
  warning: 'border-transparent bg-warning text-warning-foreground',
}

onMounted(runValidation)
watch(() => props.workstreamId, runValidation)
</script>

<template>
  <Card data-test="validation-panel">
    <CardHeader class="flex-row items-center justify-between space-y-0">
      <CardTitle>Workstream Validation</CardTitle>
      <Button variant="outline" size="sm" :disabled="loading" @click="runValidation">
        {{ loading ? 'Validating…' : 'Refresh Validation' }}
      </Button>
    </CardHeader>
    <CardContent class="grid gap-3">
      <Alert v-if="error" variant="destructive" role="alert">
        <AlertCircle class="size-4" aria-hidden="true" />
        <AlertTitle>Validation failed</AlertTitle>
        <AlertDescription>{{ error }}</AlertDescription>
      </Alert>

      <template v-if="result">
        <div
          class="flex items-center justify-between gap-2"
          :data-test="`overall-${result.overall_status}`"
        >
          <Badge :class="OVERALL_CLASS[result.overall_status]">
            {{ statusText(result.overall_status) }}
          </Badge>
          <span class="text-sm text-muted-foreground">
            Last validated: {{ formatTimestamp(result.validated_at) }}
          </span>
        </div>

        <ul class="grid gap-2">
          <ValidationCheckItem v-for="check in result.checks" :key="check.name" :check="check" />
        </ul>
      </template>

      <p v-else-if="!error && loading" class="text-sm text-muted-foreground">
        Running validation checks…
      </p>
    </CardContent>
  </Card>
</template>
