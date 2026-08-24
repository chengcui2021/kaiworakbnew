<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { AlertCircle, BadgeCheck, PackageCheck, Search } from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import { useWorkspaceService } from '../services/useWorkspaceService'
import { useDocumentService } from '../services/useDocumentService'
import { useWorkspace } from '../composables/useWorkspace'
import { useConfirm } from '@/composables/useConfirm'
import { formatNumber } from '../utils/format'
import type { ApprovalStatus, KbDocument, Workspace, WorkspaceStats } from '../types/domain'
import DocumentList from '../components/DocumentList.vue'
import WorkspaceValidationPanel from '../components/WorkspaceValidationPanel.vue'
import WorkspaceActivityPanel from '../components/WorkspaceActivityPanel.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

const props = defineProps<{ id: string }>()
const { workspaces, setActiveWorkspace, loadWorkspaces } = useWorkspace()
const { confirm } = useConfirm()
const { getWorkspace, getWorkspaceStats } = useWorkspaceService()
const { createDocument, deleteDocument, listDocuments, moveDocument, setDocumentStatus } =
  useDocumentService()

const workspace = ref<Workspace | null>(null)
const documents = ref<KbDocument[]>([])
const stats = ref<WorkspaceStats | null>(null)
const error = ref<string | null>(null)

const newDoc = ref({ title: '', content: '' })

// Bumped after any document operation so the Activity panel reloads.
const activityToken = ref(0)

// Candidate destinations for moving a document (every other workspace).
const moveTargets = computed<Workspace[]>(() => workspaces.value.filter((w) => w.id !== props.id))

async function refreshDocuments() {
  documents.value = await listDocuments(props.id)
  stats.value = await getWorkspaceStats(props.id)
  activityToken.value += 1
}

async function loadAll() {
  error.value = null
  try {
    setActiveWorkspace(props.id)
    workspace.value = await getWorkspace(props.id)
    documents.value = await listDocuments(props.id)
    stats.value = await getWorkspaceStats(props.id)
    activityToken.value += 1
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load workspace'
  }
}

async function addDocument() {
  if (!newDoc.value.title.trim()) return
  try {
    await createDocument(props.id, {
      title: newDoc.value.title.trim(),
      content: newDoc.value.content.trim(),
    })
    newDoc.value = { title: '', content: '' }
    await refreshDocuments()
    toast.success('Document added.')
  } catch (err) {
    toast.error(err instanceof Error ? err.message : 'Failed to add document')
  }
}

async function handleDelete(doc: KbDocument) {
  const ok = await confirm({
    title: `Delete "${doc.title}"?`,
    description: 'This document will be permanently removed from the workspace.',
    confirmLabel: 'Delete document',
    variant: 'destructive',
  })
  if (!ok) return
  try {
    await deleteDocument(props.id, doc.id)
    await refreshDocuments()
    toast.success('Document deleted.')
  } catch (err) {
    toast.error(err instanceof Error ? err.message : 'Delete failed')
  }
}

async function handleStatusChange(payload: { doc: KbDocument; status: ApprovalStatus }) {
  try {
    await setDocumentStatus(props.id, payload.doc.id, payload.status)
    await refreshDocuments()
    toast.success('Status updated.')
  } catch (err) {
    toast.error(err instanceof Error ? err.message : 'Failed to change status')
  }
}

async function handleMove(payload: { doc: KbDocument; targetWorkspaceId: string }) {
  const target = workspaces.value.find((w) => w.id === payload.targetWorkspaceId)
  const ok = await confirm({
    title: `Move "${payload.doc.title}"?`,
    description: `This moves the document to "${target?.name ?? payload.targetWorkspaceId}".`,
    confirmLabel: 'Move document',
  })
  if (!ok) return
  try {
    await moveDocument(props.id, payload.doc.id, payload.targetWorkspaceId)
    await refreshDocuments()
    // Refresh the shared workspace list so document counts stay accurate.
    await loadWorkspaces()
    toast.success('Document moved.')
  } catch (err) {
    toast.error(err instanceof Error ? err.message : 'Move failed')
  }
}

onMounted(loadAll)
watch(() => props.id, loadAll)
</script>

<template>
  <div class="flex flex-col gap-6">
    <Alert v-if="error" variant="destructive" role="alert">
      <AlertCircle class="size-4" aria-hidden="true" />
      <AlertTitle>Couldn't load workspace</AlertTitle>
      <AlertDescription>{{ error }}</AlertDescription>
    </Alert>

    <template v-if="workspace">
      <div>
        <h2 class="text-2xl font-semibold">{{ workspace.name }}</h2>
        <p class="mt-1 text-muted-foreground">
          {{ workspace.description || 'No description.' }}
        </p>
        <Badge variant="outline" class="mt-2">Workspace ID: {{ workspace.id }}</Badge>
        <nav class="mt-3 flex gap-2">
          <Button variant="outline" size="sm" as-child>
            <RouterLink to="/approved" class="flex items-center gap-1.5">
              <BadgeCheck class="size-4" aria-hidden="true" />
              Approved Knowledge
            </RouterLink>
          </Button>
          <Button variant="outline" size="sm" as-child>
            <RouterLink to="/packages" class="flex items-center gap-1.5">
              <PackageCheck class="size-4" aria-hidden="true" />
              Context Packages
            </RouterLink>
          </Button>
          <Button variant="outline" size="sm" as-child>
            <RouterLink to="/search" class="flex items-center gap-1.5">
              <Search class="size-4" aria-hidden="true" />
              Search this workspace
            </RouterLink>
          </Button>
        </nav>
      </div>

      <section v-if="stats" class="flex gap-4" data-test="workspace-stats">
        <Card class="flex-1">
          <CardContent class="pt-6">
            <span class="text-2xl font-bold text-primary">{{
              formatNumber(stats.document_count)
            }}</span>
            <span class="block text-sm text-muted-foreground">Documents</span>
          </CardContent>
        </Card>
        <Card class="flex-1">
          <CardContent class="pt-6">
            <span class="text-2xl font-bold text-primary">{{
              formatNumber(stats.total_characters)
            }}</span>
            <span class="block text-sm text-muted-foreground">Total characters</span>
          </CardContent>
        </Card>
      </section>

      <WorkspaceValidationPanel :workspace-id="workspace.id" />

      <WorkspaceActivityPanel
        :workspace-id="workspace.id"
        :workspace-name="workspace.name"
        :refresh-token="activityToken"
      />

      <Card>
        <CardHeader>
          <CardTitle>Add document</CardTitle>
        </CardHeader>
        <CardContent>
          <form class="grid gap-4" @submit.prevent="addDocument">
            <div class="grid gap-2">
              <Label for="doc-title">Title</Label>
              <Input
                id="doc-title"
                v-model="newDoc.title"
                required
                placeholder="Document title"
                data-test="doc-title"
              />
            </div>
            <div class="grid gap-2">
              <Label for="doc-content">Content</Label>
              <Textarea
                id="doc-content"
                v-model="newDoc.content"
                rows="3"
                placeholder="Document content"
                data-test="doc-content"
              />
            </div>
            <div>
              <Button type="submit">Add document</Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>All documents ({{ documents.length }})</CardTitle>
          <p class="text-sm text-muted-foreground">
            Set each entry's approval status (draft → approved → archived), delete it, or move it to
            another workspace — every action is recorded in the Workspace Activity panel above. Only
            <strong>approved</strong> entries can be bundled into a Context Package.
          </p>
        </CardHeader>
        <CardContent>
          <DocumentList
            :documents="documents"
            :actions="true"
            :approval="true"
            :move-targets="moveTargets"
            empty-text="No documents yet — add one above."
            @delete="handleDelete"
            @move="handleMove"
            @status-change="handleStatusChange"
          />
        </CardContent>
      </Card>
    </template>
  </div>
</template>
