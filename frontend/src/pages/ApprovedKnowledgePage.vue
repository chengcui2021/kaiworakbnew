<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { AlertCircle, AlertTriangle, BadgeCheck } from 'lucide-vue-next'
import { useDocumentService } from '../services/useDocumentService'
import { useEntryService } from '@/services/useEntryService'
import { useWorkspace } from '../composables/useWorkspace'
import { formatDate } from '../utils/format'
import type { KbDocument } from '../types/domain'
import ApprovalBadge from '../components/ApprovalBadge.vue'
import { Card, CardContent } from '@/components/ui/card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'

type ApprovedItem = KbDocument & { source: 'workspace' | 'entry'; knowledge_kind?: string; owner_scope?: string; applies_to?: string | null; priority?: number }

const { activeWorkspace } = useWorkspace()
const { listDocuments } = useDocumentService()
const { listEntries } = useEntryService()

const entries = ref<ApprovedItem[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

async function load() {
  error.value = null
  if (!activeWorkspace.value) {
    entries.value = []
    return
  }
  loading.value = true
  try {
    // Show both workspace approved documents and persistent KB entries that have
    // reached the resolved lifecycle state. Persistent KB entries are the records
    // created from Submit/Browse and are eligible for Context Packages.
    const workspaceApproved = await listDocuments(activeWorkspace.value.id, 'approved')
    const resolvedEntries = await listEntries({ status: 'resolved' })
    const persistentApproved: ApprovedItem[] = resolvedEntries.entries.map((entry) => ({
      id: entry.id,
      workspace_id: activeWorkspace.value!.id,
      title: entry.title,
      content: entry.content,
      created_at: entry.created_at,
      updated_at: entry.updated_at,
      approval_status: 'approved',
      approved_at: entry.updated_at,
      source: 'entry',
      knowledge_kind: entry.knowledge_kind,
      owner_scope: entry.owner_scope,
      applies_to: entry.applies_to,
      priority: entry.priority,
    }))
    entries.value = [
      ...workspaceApproved.map((doc): ApprovedItem => ({ ...doc, source: 'workspace' })),
      ...persistentApproved,
    ]
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load approved knowledge'
    entries.value = []
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => activeWorkspace.value?.id, load)
</script>

<template>
  <div class="flex flex-col gap-6">
    <div>
      <h2 class="flex items-center gap-2 text-2xl font-semibold">
        <BadgeCheck class="size-6" aria-hidden="true" />
        Approved Knowledge
      </h2>
      <p class="mt-1 text-muted-foreground">
        Curated, production-ready entries with <strong>approved</strong> status only. Drafts and
        archived entries are excluded.
      </p>
    </div>

    <Alert v-if="!activeWorkspace" variant="warning" data-test="no-workspace">
      <AlertTriangle class="size-4" aria-hidden="true" />
      <AlertTitle>No workspace selected</AlertTitle>
      <AlertDescription>
        Choose one from the header to view its approved knowledge.
      </AlertDescription>
    </Alert>

    <template v-else>
      <p class="text-sm text-muted-foreground" data-test="approved-scope">
        Showing approved entries in: <strong>{{ activeWorkspace.name }}</strong> ({{
          activeWorkspace.id
        }})
      </p>

      <Alert v-if="error" variant="destructive" role="alert">
        <AlertCircle class="size-4" aria-hidden="true" />
        <AlertTitle>Couldn't load approved knowledge</AlertTitle>
        <AlertDescription>{{ error }}</AlertDescription>
      </Alert>
      <p v-else-if="loading" class="text-sm text-muted-foreground">Loading approved knowledge…</p>

      <template v-else>
        <p class="text-sm text-muted-foreground" data-test="approved-count">
          {{ entries.length }} approved entr{{ entries.length === 1 ? 'y' : 'ies' }} in this
          workspace.
        </p>

        <ul v-if="entries.length" class="flex flex-col gap-3" data-test="approved-list">
          <li v-for="doc in entries" :key="doc.id">
            <Card class="border-l-4 border-l-success">
              <CardContent class="pt-6">
                <div class="flex items-center justify-between gap-2">
                  <div class="flex items-center gap-2">
                    <RouterLink
                      v-if="doc.source === 'entry'"
                      class="font-semibold underline hover:no-underline"
                      :to="{ name: 'edit-entry', params: { id: doc.id } }"
                      >{{ doc.title }}</RouterLink
                    >
                    <span v-else class="font-semibold">{{ doc.title }}</span>
                    <Badge variant="outline">{{
                      doc.source === 'entry' ? 'KB entry' : 'Workspace doc'
                    }}</Badge>
                    <Badge v-if="doc.knowledge_kind" variant="secondary">{{ doc.knowledge_kind }}</Badge>
                    <Badge v-if="doc.owner_scope" variant="outline">{{ doc.owner_scope }}</Badge>
                    <Badge v-if="doc.applies_to" variant="outline">{{ doc.applies_to }}</Badge>
                  </div>
                  <ApprovalBadge status="approved" />
                </div>
                <p class="mt-2 text-sm">{{ doc.content }}</p>
                <span
                  class="mt-2 block text-xs text-muted-foreground"
                  :data-test="`approved-meta-${doc.id}`"
                >
                  Approved {{ formatDate(doc.approved_at || doc.updated_at) }} · ID {{ doc.id }}
                </span>
              </CardContent>
            </Card>
          </li>
        </ul>

        <p v-else class="text-sm text-muted-foreground" data-test="approved-empty">
          No approved or resolved entries yet. Open Browse and mark a KB entry as
          <strong>resolved</strong>, or approve a workspace document, then it will appear here.
        </p>

        <p class="text-sm text-muted-foreground">
          Ready to bundle these into a verified package?
          <RouterLink class="underline hover:no-underline" to="/packages"
            >Create a Context Package →</RouterLink
          >
        </p>
      </template>
    </template>
  </div>
</template>
