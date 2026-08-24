<script setup lang="ts">
import { onMounted, ref, watch, type Component } from 'vue'
import {
  Archive,
  ArrowRightLeft,
  Circle,
  CheckCircle2,
  FileEdit,
  FolderPlus,
  Pencil,
  Trash2,
  Upload,
  Lock,
  AlertCircle,
} from 'lucide-vue-next'
import { useWorkspaceService } from '../services/useWorkspaceService'
import { formatDateTime, formatRelativeTime } from '../utils/format'
import type { WorkspaceActivity } from '../types/domain'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

const props = defineProps<{
  workspaceId: string
  workspaceName: string
  // Bumping this token forces a reload (e.g. after upload / delete / move).
  refreshToken?: number
}>()

const { listActivities } = useWorkspaceService()

const activities = ref<WorkspaceActivity[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

const EVENT_META: Record<string, { icon: Component; label: string }> = {
  workspace_created: { icon: FolderPlus, label: 'Workspace created' },
  workspace_renamed: { icon: Pencil, label: 'Workspace renamed' },
  document_uploaded: { icon: Upload, label: 'Document uploaded' },
  document_deleted: { icon: Trash2, label: 'Document deleted' },
  document_moved: { icon: ArrowRightLeft, label: 'Document moved' },
  document_approved: { icon: CheckCircle2, label: 'KB entry approved' },
  document_archived: { icon: Archive, label: 'KB entry archived' },
  document_drafted: { icon: FileEdit, label: 'KB entry set to draft' },
  package_created: { icon: Lock, label: 'Context Package created' },
}

function meta(type: string) {
  return EVENT_META[type] || { icon: Circle, label: type }
}

async function load() {
  if (!props.workspaceId) return
  loading.value = true
  error.value = null
  try {
    // Scoped to this workspace only; backend returns the latest 20 newest-first.
    activities.value = await listActivities(props.workspaceId, 20)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load activity'
    activities.value = []
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => props.workspaceId, load)
watch(() => props.refreshToken, load)
</script>

<template>
  <Card data-test="activity-panel">
    <CardHeader class="flex-row items-center justify-between space-y-0">
      <div>
        <CardTitle>Workspace Activity</CardTitle>
        <p class="text-sm text-muted-foreground" data-test="activity-scope">
          Activity in <strong>{{ workspaceName }}</strong> ({{ workspaceId }})
        </p>
      </div>
      <Button variant="outline" size="sm" :disabled="loading" @click="load">
        {{ loading ? 'Loading…' : 'Refresh' }}
      </Button>
    </CardHeader>
    <CardContent class="grid gap-3">
      <p class="text-sm text-muted-foreground">
        Showing the latest 20 activity records, newest first.
      </p>

      <Alert v-if="error" variant="destructive" role="alert">
        <AlertCircle class="size-4" aria-hidden="true" />
        <AlertTitle>Couldn't load activity</AlertTitle>
        <AlertDescription>{{ error }}</AlertDescription>
      </Alert>

      <ul
        v-if="activities.length"
        class="grid max-h-96 gap-2 overflow-y-auto"
        data-test="activity-list"
      >
        <li
          v-for="act in activities"
          :key="act.id"
          class="flex items-start gap-3 rounded-md border p-3"
          :data-test="`activity-${act.event_type}`"
        >
          <component
            :is="meta(act.event_type).icon"
            class="mt-0.5 size-4 shrink-0 text-muted-foreground"
            aria-hidden="true"
          />
          <div class="flex-1">
            <span class="block text-sm font-medium">{{ act.description }}</span>
            <span class="flex items-center gap-1 text-xs text-muted-foreground">
              <span>{{ meta(act.event_type).label }}</span>
              <span aria-hidden="true">·</span>
              <time :datetime="act.timestamp" :title="formatDateTime(act.timestamp)">
                {{ formatRelativeTime(act.timestamp) }} — {{ formatDateTime(act.timestamp) }}
              </time>
            </span>
          </div>
        </li>
      </ul>

      <p
        v-else-if="!loading && !error"
        class="text-sm text-muted-foreground"
        data-test="activity-empty"
      >
        No activity recorded for this workspace yet.
      </p>
    </CardContent>
  </Card>
</template>
