<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { useWorkspaceService } from '../services/useWorkspaceService'
import { useDocumentService } from '../services/useDocumentService'
import { usePackageService } from '../services/usePackageService'
import { useEntryService } from '@/services/useEntryService'
import { useWorkspace } from '../composables/useWorkspace'
import { useConfirm } from '@/composables/useConfirm'
import { formatDate, formatDateTime } from '../utils/format'
import type { Workspace } from '../types/domain'
import WorkspaceForm from '../components/WorkspaceForm.vue'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const router = useRouter()
const { workspaces, activeWorkspace, activeWorkspaceId, loadWorkspaces, setActiveWorkspace } =
  useWorkspace()
const { createWorkspace, deleteWorkspace, updateWorkspace } = useWorkspaceService()
const { listDocuments } = useDocumentService()
const { listContextPackages } = usePackageService()
const { listEntries } = useEntryService()
const { confirm } = useConfirm()

const NOT_AVAILABLE = 'Not available'
const approvedCount = ref<number | null>(null)
const packageCount = ref<number | null>(null)
const resolvedKbCount = ref<number | null>(null)

async function loadStatusSummary() {
  const ws = activeWorkspace.value
  approvedCount.value = null
  packageCount.value = null
  resolvedKbCount.value = null
  if (!ws) return
  try {
    const [workspaceApproved, packages, resolvedKb] = await Promise.all([
      listDocuments(ws.id, 'approved'),
      listContextPackages(ws.id),
      listEntries({ status: 'resolved' }),
    ])
    approvedCount.value = workspaceApproved.length + resolvedKb.entries.length
    packageCount.value = packages.length
    resolvedKbCount.value = resolvedKb.entries.length
  } catch {
    // Keep the page usable even if a secondary status endpoint is unavailable.
    approvedCount.value = null
    packageCount.value = null
    resolvedKbCount.value = null
  }
}

const statusFields = computed(() => {
  const ws = activeWorkspace.value
  const readyCount = (ws?.document_count || 0) + (resolvedKbCount.value || 0)
  return [
    { label: 'Active Workspace', value: ws?.name || NOT_AVAILABLE },
    {
      label: 'Approved Knowledge Entries',
      value: approvedCount.value === null ? NOT_AVAILABLE : String(approvedCount.value),
    },
    {
      label: 'Context Packages',
      value: packageCount.value === null ? NOT_AVAILABLE : String(packageCount.value),
    },
    {
      label: 'Search Readiness',
      value: ws ? (readyCount > 0 ? 'Ready' : 'No documents') : NOT_AVAILABLE,
    },
    {
      label: 'Last Synchronization Time',
      value: ws?.updated_at ? formatDateTime(ws.updated_at) : NOT_AVAILABLE,
    },
  ]
})

const editing = ref<Workspace | null>(null)
const showCreate = ref(false)
const busy = ref(false)

async function handleCreate(payload: { name: string; description: string }) {
  busy.value = true
  try {
    const ws = await createWorkspace(payload)
    await loadWorkspaces()
    setActiveWorkspace(ws.id)
    await loadStatusSummary()
    toast.success(`Created workspace "${ws.name}".`)
    showCreate.value = false
  } finally {
    busy.value = false
  }
}

async function handleUpdate(payload: { name: string; description: string }) {
  if (!editing.value) return
  busy.value = true
  try {
    await updateWorkspace(editing.value.id, payload)
    await loadWorkspaces()
    await loadStatusSummary()
    toast.success(`Updated workspace "${payload.name}".`)
    editing.value = null
  } finally {
    busy.value = false
  }
}

async function handleDelete(ws: Workspace) {
  const ok = await confirm({
    title: `Delete "${ws.name}"?`,
    description:
      'This permanently deletes the workspace and all of its documents. This cannot be undone.',
    confirmLabel: 'Delete workspace',
    variant: 'destructive',
    requireText: ws.name,
  })
  if (!ok) return
  busy.value = true
  try {
    await deleteWorkspace(ws.id)
    if (activeWorkspaceId.value === ws.id) setActiveWorkspace(null)
    await loadWorkspaces()
    await loadStatusSummary()
    toast.success(`Deleted workspace "${ws.name}".`)
  } finally {
    busy.value = false
  }
}

function open(ws: Workspace) {
  setActiveWorkspace(ws.id)
  router.push(`/workspaces/${ws.id}`)
}

onMounted(async () => {
  await loadWorkspaces()
  await loadStatusSummary()
})
watch(() => activeWorkspace.value?.id, loadStatusSummary)
</script>

<template>
  <div class="flex flex-col gap-6">
    <div>
      <div class="flex items-center justify-between gap-4">
        <h2 class="text-2xl font-semibold">Workspaces</h2>
        <Button data-test="ws-new" @click="showCreate = true">+ New workspace</Button>
      </div>
      <p class="mt-1 text-muted-foreground">
        Manage isolated knowledge bases. Each workspace keeps its own documents and search scope.
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

    <WorkspaceForm
      v-model:open="showCreate"
      submit-label="Create workspace"
      @submit="handleCreate"
    />

    <WorkspaceForm
      :open="!!editing"
      :workspace="editing"
      submit-label="Save changes"
      @update:open="(value) => !value && (editing = null)"
      @submit="handleUpdate"
    />

    <section
      class="grid grid-cols-[repeat(auto-fill,minmax(260px,1fr))] gap-4"
      data-test="workspace-grid"
    >
      <Card
        v-for="ws in workspaces"
        :key="ws.id"
        :class="{
          'border-primary shadow-[0_0_0_2px_var(--color-primary)]/20': ws.id === activeWorkspaceId,
        }"
      >
        <CardHeader>
          <div class="flex items-center justify-between">
            <CardTitle>{{ ws.name }}</CardTitle>
            <Badge v-if="ws.id === activeWorkspaceId">Active</Badge>
          </div>
        </CardHeader>
        <CardContent class="flex flex-col gap-3">
          <p class="flex-1 text-sm text-muted-foreground">
            {{ ws.description || 'No description.' }}
          </p>
          <dl class="flex gap-6">
            <div>
              <dt class="text-xs uppercase text-muted-foreground">Documents</dt>
              <dd class="font-semibold">{{ ws.document_count }}</dd>
            </div>
            <div>
              <dt class="text-xs uppercase text-muted-foreground">Created</dt>
              <dd class="font-semibold">{{ formatDate(ws.created_at) }}</dd>
            </div>
          </dl>
          <div class="flex flex-wrap gap-2">
            <Button size="sm" @click="open(ws)">Open</Button>
            <Button variant="outline" size="sm" @click="setActiveWorkspace(ws.id)">
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
