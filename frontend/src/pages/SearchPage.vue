<script setup lang="ts">
import { computed, ref } from 'vue'
import { AlertTriangle } from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import { useSearchService } from '../services/useSearchService'
import { useEntryService } from '../services/useEntryService'
import { useWorkspace } from '../composables/useWorkspace'
import type { KbDocument, SearchResultItem as WorkspaceSearchResultItem } from '../types/domain'
import type {
  ComponentName,
  Entry,
  EntryPatchStatus,
  EntryType,
  SearchResultItem as EntrySearchResultItem,
} from '@/types/entry'
import DocumentList from '../components/DocumentList.vue'
import SearchBar from '../components/SearchBar.vue'
import EntryCard from '@/components/EntryCard.vue'
import FilterBar from '@/components/FilterBar.vue'
import { Card, CardContent } from '@/components/ui/card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'

const { activeWorkspace } = useWorkspace()
const { searchDocuments } = useSearchService()
const { searchEntries } = useEntryService()

const scope = ref<'workspace' | 'entries'>(activeWorkspace.value ? 'workspace' : 'entries')

// Shared across both scopes so switching tabs doesn't discard what the user
// typed — SearchBar is a controlled component (`v-model`), so even though a
// fresh instance mounts per scope branch, it's seeded with this value.
const query = ref('')

const workspaceResults = ref<WorkspaceSearchResultItem[] | null>(null)
const entryResults = ref<EntrySearchResultItem[] | null>(null)
const lastQuery = ref('')
const loading = ref(false)

const filterType = ref('')
const filterComponent = ref('')
const filterStatus = ref('')
const filterTag = ref('')
const entryLimit = ref(10)

const docs = computed<KbDocument[]>(() => (workspaceResults.value || []).map((r) => r.document))

async function runWorkspaceSearch(searchQuery: string) {
  if (!activeWorkspace.value) {
    toast.error('Select a workspace before searching.')
    return
  }
  lastQuery.value = searchQuery
  try {
    const response = await searchDocuments(activeWorkspace.value.id, searchQuery)
    workspaceResults.value = response.results
  } catch (err) {
    toast.error(err instanceof Error ? err.message : 'Search failed')
  }
}

async function runEntrySearch(searchQuery: string) {
  lastQuery.value = searchQuery
  try {
    const response = await searchEntries(searchQuery, {
      type: (filterType.value || undefined) as EntryType | undefined,
      component: (filterComponent.value || undefined) as ComponentName | undefined,
      status: (filterStatus.value || undefined) as EntryPatchStatus | undefined,
      tag: filterTag.value || undefined,
      limit: entryLimit.value,
    })
    entryResults.value = response.results
  } catch (err) {
    toast.error(err instanceof Error ? err.message : 'Search failed')
  }
}

async function runSearch(searchQuery: string) {
  loading.value = true
  workspaceResults.value = null
  entryResults.value = null
  try {
    if (scope.value === 'workspace') {
      await runWorkspaceSearch(searchQuery)
    } else {
      await runEntrySearch(searchQuery)
    }
  } finally {
    loading.value = false
  }
}

function onEntryUpdated(updated: Entry, index: number) {
  if (!entryResults.value) return
  entryResults.value[index] = { ...entryResults.value[index], ...updated }
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <div>
      <h2 class="text-2xl font-semibold">Search</h2>
      <p class="mt-1 text-muted-foreground">
        Search all KB entries, or scope to the active workspace's documents.
      </p>
    </div>

    <Tabs v-model="scope">
      <TabsList aria-label="Search scope">
        <TabsTrigger value="entries">All KB entries</TabsTrigger>
        <TabsTrigger value="workspace">Active workspace documents</TabsTrigger>
      </TabsList>
    </Tabs>

    <template v-if="scope === 'workspace'">
      <Alert v-if="!activeWorkspace" variant="warning" data-test="no-workspace">
        <AlertTriangle class="size-4" aria-hidden="true" />
        <AlertTitle>No workspace selected</AlertTitle>
        <AlertDescription> Choose one from the header to enable search. </AlertDescription>
      </Alert>

      <template v-else>
        <p class="text-sm text-muted-foreground" data-test="search-scope">
          Searching in: <strong>{{ activeWorkspace.name }}</strong> ({{ activeWorkspace.id }})
        </p>
        <SearchBar v-model="query" :disabled="!activeWorkspace" @search="runSearch" />

        <p v-if="loading" class="text-sm text-muted-foreground">Searching…</p>

        <Card v-if="workspaceResults !== null">
          <CardContent class="pt-6">
            <p class="mb-2 text-sm text-muted-foreground" data-test="search-summary">
              {{ docs.length }} result(s) for "{{ lastQuery }}" in {{ activeWorkspace.name }}.
            </p>
            <DocumentList :documents="docs" empty-text="No matching documents in this workspace." />
          </CardContent>
        </Card>
      </template>
    </template>

    <template v-else>
      <Card>
        <CardContent class="grid gap-4 pt-6">
          <FilterBar
            v-model:type="filterType"
            v-model:component="filterComponent"
            v-model:status="filterStatus"
            v-model:tag="filterTag"
            v-model:limit="entryLimit"
            :show-limit="true"
          />
          <SearchBar v-model="query" placeholder="Search all KB entries…" @search="runSearch" />
        </CardContent>
      </Card>

      <p v-if="loading" class="text-sm text-muted-foreground">Searching…</p>

      <template v-if="entryResults !== null">
        <p class="text-sm text-muted-foreground">
          {{ entryResults.length }} result{{ entryResults.length === 1 ? '' : 's' }} for "{{
            lastQuery
          }}"
        </p>
        <div v-if="entryResults.length" class="grid gap-4">
          <EntryCard
            v-for="(item, i) in entryResults"
            :key="item.id"
            :entry="item"
            :similarity="item.similarity"
            :rank="i + 1"
            readonly
            @updated="(e) => onEntryUpdated(e, i)"
          />
        </div>
        <p v-else class="text-sm text-muted-foreground">Try different wording or remove filters.</p>
      </template>
    </template>
  </div>
</template>
