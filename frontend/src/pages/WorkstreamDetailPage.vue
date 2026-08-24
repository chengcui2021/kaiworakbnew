<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { AlertCircle, BadgeCheck, PackageCheck, Plus, Search } from 'lucide-vue-next'
import { useWorkstreamService } from '@/services/useWorkstreamService'
import { useEntryService } from '@/services/useEntryService'
import { useWorkstream } from '@/composables/useWorkstream'
import { formatNumber } from '@/utils/format'
import type { Workstream, WorkstreamStats } from '@/types/domain'
import type { Entry } from '@/types/entry'
import EntryCard from '@/components/EntryCard.vue'
import WorkstreamValidationPanel from '@/components/WorkstreamValidationPanel.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

const props = defineProps<{ id: string }>()
const { setActiveWorkstream } = useWorkstream()
const { getWorkstream, getWorkstreamStats } = useWorkstreamService()
const { listEntries } = useEntryService()

const workstream = ref<Workstream | null>(null)
const recentEntries = ref<Entry[]>([])
const stats = ref<WorkstreamStats | null>(null)
const error = ref<string | null>(null)

async function loadAll() {
  error.value = null
  try {
    setActiveWorkstream(props.id)
    workstream.value = await getWorkstream(props.id)
    stats.value = await getWorkstreamStats(props.id)
    const result = await listEntries({ workstream_id: props.id, limit: 10 })
    recentEntries.value = result.entries
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load workstream'
  }
}

onMounted(loadAll)
watch(() => props.id, loadAll)
</script>

<template>
  <div class="flex flex-col gap-6">
    <Alert v-if="error" variant="destructive" role="alert">
      <AlertCircle class="size-4" aria-hidden="true" />
      <AlertTitle>Couldn't load workstream</AlertTitle>
      <AlertDescription>{{ error }}</AlertDescription>
    </Alert>

    <template v-if="workstream">
      <div>
        <h2 class="text-2xl font-semibold">{{ workstream.name }}</h2>
        <p class="mt-1 text-muted-foreground">
          {{ workstream.description || 'No description.' }}
        </p>
        <Badge variant="outline" class="mt-2">Workstream ID: {{ workstream.id }}</Badge>
        <nav class="mt-3 flex gap-2">
          <Button variant="outline" size="sm" as-child>
            <RouterLink to="/submit" class="flex items-center gap-1.5">
              <Plus class="size-4" aria-hidden="true" />
              Submit new entry
            </RouterLink>
          </Button>
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
              Search this workstream
            </RouterLink>
          </Button>
        </nav>
      </div>

      <section v-if="stats" class="flex gap-4" data-test="workstream-stats">
        <Card class="flex-1">
          <CardContent class="pt-6">
            <span class="text-2xl font-bold text-primary">{{
              formatNumber(stats.entry_count)
            }}</span>
            <span class="block text-sm text-muted-foreground">Entries</span>
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

      <WorkstreamValidationPanel :workstream-id="workstream.id" />

      <Card>
        <CardHeader>
          <CardTitle>Recent entries ({{ recentEntries.length }})</CardTitle>
          <p class="text-sm text-muted-foreground">
            Latest entries in this workstream, newest first.
          </p>
        </CardHeader>
        <CardContent>
          <div v-if="recentEntries.length" class="grid gap-3">
            <EntryCard v-for="entry in recentEntries" :key="entry.id" :entry="entry" readonly />
          </div>
          <p v-else class="text-sm text-muted-foreground">
            No entries yet.
            <RouterLink class="underline hover:no-underline" to="/submit">Submit one →</RouterLink>
          </p>
        </CardContent>
      </Card>
    </template>
  </div>
</template>
