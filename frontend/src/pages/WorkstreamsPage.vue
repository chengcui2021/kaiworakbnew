<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { useWorkstreamService } from '@/services/useWorkstreamService'
import { useEntryService } from '@/services/useEntryService'
import { useWorkstream } from '@/composables/useWorkstream'
import { useConfirm } from '@/composables/useConfirm'
import { formatDate, formatDateTime } from '@/utils/format'
import type { Workstream } from '@/types/domain'
import WorkstreamForm from '@/components/WorkstreamForm.vue'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const router = useRouter()
const { workstreams, activeWorkstream, activeWorkstreamId, loadWorkstreams, setActiveWorkstream } =
  useWorkstream()
const { createWorkstream, deleteWorkstream, updateWorkstream } = useWorkstreamService()
const { listEntries } = useEntryService()
const { confirm } = useConfirm()

const NOT_AVAILABLE = 'Not available'
const approvedCount = ref<number | null>(null)

async function loadStatusSummary() {
  const ws = activeWorkstream.value
  approvedCount.value = null
  if (!ws) return
  try {
    const resolvedKb = await listEntries({ workstream_id: ws.id, status: 'resolved' })
    approvedCount.value = resolvedKb.entries.length
  } catch {
    approvedCount.value = null
  }
}

const statusFields = computed(() => {
  const ws = activeWorkstream.value
  return [
    { label: 'Active Workstream', value: ws?.name || NOT_AVAILABLE },
    {
      label: 'Resolved Entries',
      value: approvedCount.value === null ? NOT_AVAILABLE : String(approvedCount.value),
    },
    {
      label: 'Search Readiness',
      value: ws ? (ws.entry_count > 0 ? 'Ready' : 'No entries') : NOT_AVAILABLE,
    },
    {
      label: 'Last Synchronization Time',
      value: ws?.updated_at ? formatDateTime(ws.updated_at) : NOT_AVAILABLE,
    },
  ]
})

const editing = ref<Workstream | null>(null)
const showCreate = ref(false)
const busy = ref(false)

async function handleCreate(payload: { name: string; description: string }) {
  busy.value = true
  try {
    const ws = await createWorkstream(payload)
    await loadWorkstreams()
    setActiveWorkstream(ws.id)
    await loadStatusSummary()
    toast.success(`Created workstream "${ws.name}".`)
    showCreate.value = false
  } finally {
    busy.value = false
  }
}

async function handleUpdate(payload: { name: string; description: string }) {
  if (!editing.value) return
  busy.value = true
  try {
    await updateWorkstream(editing.value.id, payload)
    await loadWorkstreams()
    await loadStatusSummary()
    toast.success(`Updated workstream "${payload.name}".`)
    editing.value = null
  } finally {
    busy.value = false
  }
}

async function handleDelete(ws: Workstream) {
  const ok = await confirm({
    title: `Delete "${ws.name}"?`,
    description:
      'This permanently deletes the workstream. Entries will become unassigned but are not deleted.',
    confirmLabel: 'Delete workstream',
    variant: 'destructive',
    requireText: ws.name,
  })
  if (!ok) return
  busy.value = true
  try {
    await deleteWorkstream(ws.id)
    if (activeWorkstreamId.value === ws.id) setActiveWorkstream(null)
    await loadWorkstreams()
    await loadStatusSummary()
    toast.success(`Deleted workstream "${ws.name}".`)
  } finally {
    busy.value = false
  }
}

function open(ws: Workstream) {
  setActiveWorkstream(ws.id)
  router.push(`/workstreams/${ws.id}`)
}

onMounted(async () => {
  await loadWorkstreams()
  await loadStatusSummary()
})
watch(() => activeWorkstream.value?.id, loadStatusSummary)
</script>

<template>
  <div class="flex flex-col gap-6">
    <div>
      <div class="flex items-center justify-between gap-4">
        <h2 class="text-2xl font-semibold">Workstreams</h2>
        <Button data-test="ws-new" @click="showCreate = true">+ New workstream</Button>
      </div>
      <p class="mt-1 text-muted-foreground">
        Manage isolated knowledge bases. Each workstream keeps its own entries and search scope.
      </p>
    </div>

    <Card data-test="kb-status-panel">
      <CardHeader>
        <CardTitle>Knowledge Base Status</CardTitle>
      </CardHeader>
      <CardContent>
        <dl class="flex flex-wrap gap-x-8 gap-y-4">
          <div v-for="field in statusFields" :key="field.label">
            <dt class="text-xs uppercase text-muted-foreground">{{ field.label }}</dt>
            <dd
              class="font-semibold"
              :class="{
                'italic font-normal text-muted-foreground': field.value === 'Not available',
              }"
            >
              {{ field.value }}
            </dd>
          </div>
        </dl>
      </CardContent>
    </Card>

    <WorkstreamForm
      v-model:open="showCreate"
      submit-label="Create workstream"
      @submit="handleCreate"
    />

    <WorkstreamForm
      :open="!!editing"
      :workstream="editing"
      submit-label="Save changes"
      @update:open="(value) => !value && (editing = null)"
      @submit="handleUpdate"
    />

    <section
      class="grid grid-cols-[repeat(auto-fill,minmax(260px,1fr))] gap-4"
      data-test="workstream-grid"
    >
      <Card
        v-for="ws in workstreams"
        :key="ws.id"
        :class="{
          'border-primary shadow-[0_0_0_2px_var(--color-primary)]/20': ws.id === activeWorkstreamId,
        }"
      >
        <CardHeader>
          <div class="flex items-center justify-between">
            <CardTitle>{{ ws.name }}</CardTitle>
            <Badge v-if="ws.id === activeWorkstreamId">Active</Badge>
          </div>
        </CardHeader>
        <CardContent class="flex flex-col gap-3">
          <p class="flex-1 text-sm text-muted-foreground">
            {{ ws.description || 'No description.' }}
          </p>
          <dl class="flex gap-6">
            <div>
              <dt class="text-xs uppercase text-muted-foreground">Entries</dt>
              <dd class="font-semibold">{{ ws.entry_count }}</dd>
            </div>
            <div>
              <dt class="text-xs uppercase text-muted-foreground">Created</dt>
              <dd class="font-semibold">{{ formatDate(ws.created_at) }}</dd>
            </div>
          </dl>
          <div class="flex flex-wrap gap-2">
            <Button size="sm" @click="open(ws)">Open</Button>
            <Button variant="outline" size="sm" @click="setActiveWorkstream(ws.id)">
              Set active
            </Button>
            <Button variant="outline" size="sm" @click="editing = ws">Edit</Button>
            <Button variant="destructive" size="sm" :disabled="busy" @click="handleDelete(ws)">
              Delete
            </Button>
          </div>
        </CardContent>
      </Card>
    </section>
  </div>
</template>
