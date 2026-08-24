<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { AlertCircle, AlertTriangle } from 'lucide-vue-next'
import { useEntryService } from '@/services/useEntryService'
import { useDocumentService } from '@/services/useDocumentService'
import { useWorkspace } from '@/composables/useWorkspace'
import type { Entry, EntryPatchStatus, ComponentName, EntryType } from '@/types/entry'
import type { KbDocument } from '@/types/domain'
import { formatDateTime } from '@/utils/format'
import EntryCard from '@/components/EntryCard.vue'
import FilterBar from '@/components/FilterBar.vue'
import { Card, CardContent } from '@/components/ui/card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'

const { listEntries } = useEntryService()
const { listDocuments } = useDocumentService()
const { activeWorkspace } = useWorkspace()

// Mirrors SearchPage.vue's scope toggle so "scope to a workspace" behaves
// identically everywhere in the app — the workspace itself is always picked
// via the header switcher, never a second, page-local picker.
const scope = ref<'entries' | 'workspace'>(activeWorkspace.value ? 'workspace' : 'entries')

const filterType = ref('')
const filterComponent = ref('')
const filterStatus = ref('')
const filterTag = ref('')
const limit = ref(20)
const offset = ref(0)

const loading = ref(false)
const entries = ref<Entry[]>([])
const total = ref(0)
const loadError = ref('')

const workspaceDocuments = ref<KbDocument[]>([])
const workspaceLoading = ref(false)

const browsingWorkspaceDocuments = computed(() => scope.value === 'workspace')

const page = computed(() => Math.floor(offset.value / limit.value) + 1)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / limit.value)))

function documentPreview(document: KbDocument): string {
  const content = document.content?.trim() || 'No content yet.'
  return content.length > 220 ? `${content.slice(0, 220)}…` : content
}

async function loadWorkspaceDocuments() {
  if (!activeWorkspace.value) return
  workspaceLoading.value = true
  loadError.value = ''
  entries.value = []
  total.value = 0
  try {
    workspaceDocuments.value = await listDocuments(activeWorkspace.value.id)
  } catch (err) {
    workspaceDocuments.value = []
    loadError.value = err instanceof Error ? err.message : String(err)
  } finally {
    workspaceLoading.value = false
  }
}

async function loadEntries() {
  if (browsingWorkspaceDocuments.value) {
    await loadWorkspaceDocuments()
    return
  }

  loading.value = true
  loadError.value = ''
  workspaceDocuments.value = []

  try {
    const data = await listEntries({
      type: (filterType.value || undefined) as EntryType | undefined,
      component: (filterComponent.value || undefined) as ComponentName | undefined,
      status: (filterStatus.value || undefined) as EntryPatchStatus | undefined,
      tag: filterTag.value || undefined,
      limit: limit.value,
      offset: offset.value,
    })
    entries.value = data.entries
    total.value = data.total
  } catch (err) {
    loadError.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  offset.value = 0
  loadEntries()
}

function prevPage() {
  offset.value = Math.max(0, offset.value - limit.value)
  loadEntries()
}

function nextPage() {
  if (offset.value + limit.value < total.value) {
    offset.value += limit.value
    loadEntries()
  }
}

function onEntryUpdated(updated: Entry, index: number) {
  entries.value[index] = updated
}

function onEntryDeleted(id: string) {
  entries.value = entries.value.filter((e) => e.id !== id)
  total.value = Math.max(0, total.value - 1)
}

watch(limit, () => {
  offset.value = 0
})

watch(scope, () => {
  offset.value = 0
  loadEntries()
})

watch(
  () => activeWorkspace.value?.id,
  () => {
    if (browsingWorkspaceDocuments.value) loadEntries()
  }
)

loadEntries()
</script>

<template>
  <div class="flex flex-col gap-6">
    <div>
      <h2 class="text-2xl font-semibold">Browse entries</h2>
      <p class="mt-1 text-muted-foreground">
        List and filter knowledge base records, or browse the active workspace's documents.
      </p>
    </div>

    <Tabs v-model="scope">
      <TabsList aria-label="Browse scope">
        <TabsTrigger value="entries">All KB entries</TabsTrigger>
        <TabsTrigger value="workspace" :disabled="!activeWorkspace">
          Active workspace documents
        </TabsTrigger>
      </TabsList>
    </Tabs>

    <Alert
      v-if="scope === 'workspace' && !activeWorkspace"
      variant="warning"
      data-test="no-workspace"
    >
      <AlertTriangle class="size-4" aria-hidden="true" />
      <AlertTitle>No workspace selected</AlertTitle>
      <AlertDescription> Choose one from the header to browse its documents. </AlertDescription>
    </Alert>

    <template v-else-if="scope === 'workspace'">
      <p class="text-sm text-muted-foreground" data-test="browse-scope">
        Browsing documents in: <strong>{{ activeWorkspace!.name }}</strong>
      </p>
    </template>

    <Card v-if="scope === 'entries'">
      <CardContent class="grid gap-4 pt-6">
        <FilterBar
          v-model:type="filterType"
          v-model:component="filterComponent"
          v-model:status="filterStatus"
          v-model:tag="filterTag"
        />
        <div class="flex items-end gap-3">
          <div class="grid gap-1.5">
            <Label for="browse-limit">Per page</Label>
            <Select v-model="limit">
              <SelectTrigger id="browse-limit" size="sm" class="w-20"
                ><SelectValue
              /></SelectTrigger>
              <SelectContent>
                <SelectItem :value="10">10</SelectItem>
                <SelectItem :value="20">20</SelectItem>
                <SelectItem :value="50">50</SelectItem>
                <SelectItem :value="100">100</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Button type="button" :disabled="loading" @click="applyFilters">
            {{ loading ? 'Loading…' : 'Apply filters' }}
          </Button>
        </div>
      </CardContent>
    </Card>

    <p v-if="browsingWorkspaceDocuments && activeWorkspace" class="text-sm text-muted-foreground">
      Showing {{ workspaceDocuments.length }} document{{
        workspaceDocuments.length === 1 ? '' : 's'
      }}
      in
      {{ activeWorkspace.name }}
    </p>
    <p v-else-if="total > 0" class="text-sm text-muted-foreground">
      Showing {{ entries.length }} of {{ total }} entries
      <span v-if="totalPages > 1">· Page {{ page }} / {{ totalPages }}</span>
    </p>

    <Alert v-if="loadError" variant="destructive" role="alert">
      <AlertCircle class="size-4" aria-hidden="true" />
      <AlertTitle
        >Couldn't load {{ browsingWorkspaceDocuments ? 'documents' : 'entries' }}</AlertTitle
      >
      <AlertDescription>{{ loadError }}</AlertDescription>
    </Alert>

    <section v-if="browsingWorkspaceDocuments" class="grid gap-3">
      <p v-if="workspaceLoading" class="text-sm text-muted-foreground">
        Loading workspace documents…
      </p>
      <p v-else-if="!loadError && !workspaceDocuments.length" class="text-sm text-muted-foreground">
        This workspace does not have documents yet.
      </p>
      <ul v-else-if="workspaceDocuments.length" class="grid gap-3">
        <li v-for="document in workspaceDocuments" :key="document.id">
          <Card
            :class="document.approval_status === 'approved' ? 'border-l-4 border-l-success' : ''"
          >
            <CardContent class="pt-6">
              <div class="flex items-center justify-between gap-2">
                <strong>{{
                  document.title || document.content?.slice(0, 80) || 'Untitled document'
                }}</strong>
                <Badge variant="outline">{{ document.approval_status }}</Badge>
              </div>
              <p class="mt-2 text-sm">{{ documentPreview(document) }}</p>
              <p class="mt-2 text-xs text-muted-foreground">
                Workspace: {{ activeWorkspace?.name }} · ID {{ document.id }} · Updated
                {{ formatDateTime(document.updated_at) }}
              </p>
            </CardContent>
          </Card>
        </li>
      </ul>
    </section>

    <section v-else-if="entries.length" class="grid gap-4">
      <EntryCard
        v-for="(item, i) in entries"
        :key="item.id"
        :entry="item"
        readonly
        allow-delete
        @updated="(e) => onEntryUpdated(e, i)"
        @deleted="onEntryDeleted"
      />
    </section>
    <p v-else-if="!loading && !loadError" class="text-sm text-muted-foreground">
      No records match these filters.
    </p>

    <nav v-if="!browsingWorkspaceDocuments && total > limit" class="flex gap-2">
      <Button type="button" variant="outline" :disabled="loading || offset === 0" @click="prevPage"
        >Previous</Button
      >
      <Button
        type="button"
        variant="outline"
        :disabled="loading || offset + limit >= total"
        @click="nextPage"
      >
        Next
      </Button>
    </nav>
  </div>
</template>
