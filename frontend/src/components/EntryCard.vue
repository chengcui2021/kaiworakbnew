<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { useEntryService } from '@/services/useEntryService'
import { useConfirm } from '@/composables/useConfirm'
import { PATCH_STATUSES } from '@/constants/entryOptions'
import { formatDateTime, formatSimilarity } from '@/utils/format'
import type { Entry, EntryPatchStatus } from '@/types/entry'
import JiraLinksPanel from './JiraLinksPanel.vue'
import MarkdownContent from './MarkdownContent.vue'
import TagsPanel from './TagsPanel.vue'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Pencil, Trash2 } from 'lucide-vue-next'

const router = useRouter()
const { patchEntryStatus, deleteEntry } = useEntryService()
const { confirm } = useConfirm()

const props = withDefaults(
  defineProps<{
    entry: Entry
    similarity?: number | null
    rank?: number | null
    allowStatusPatch?: boolean
    /**
     * Render as a scannable, non-interactive summary for list contexts
     * (Browse/Search results) instead of the fully-editable detail view.
     * Suppresses the Tags/Jira-links panels (each fetches on mount — firing
     * one per row is why list pages were making 40+ requests just to paint)
     * and the inline status-patch control. Tags still show as read-only
     * badges (already present on the Entry payload); Jira links don't,
     * since the list/search response doesn't include them — follow the
     * "Edit" action through to the entry's detail page for those.
     */
    readonly?: boolean
    /** Shows a destructive Delete icon button next to Edit, for list pages that manage entries directly. */
    allowDelete?: boolean
  }>(),
  { similarity: null, rank: null, allowStatusPatch: true, readonly: false, allowDelete: false }
)

const emit = defineEmits<{ updated: [entry: Entry]; deleted: [id: string] }>()

const expanded = ref(false)
const patchStatus = ref<EntryPatchStatus>(props.entry.status as EntryPatchStatus)
const patching = ref(false)
const patchMessage = ref('')
const deleting = ref(false)

const showEditableFooter = computed(() => props.allowStatusPatch && !props.readonly)

watch(
  () => props.entry.status,
  (s) => {
    patchStatus.value = s as EntryPatchStatus
  }
)

async function applyStatus() {
  if (patchStatus.value === props.entry.status) return
  patching.value = true
  patchMessage.value = ''
  try {
    const updated = await patchEntryStatus(props.entry.id, patchStatus.value)
    emit('updated', updated)
    patchMessage.value = 'Status updated.'
  } catch (err) {
    patchMessage.value = err instanceof Error ? err.message : 'Update failed'
    patchStatus.value = props.entry.status as EntryPatchStatus
  } finally {
    patching.value = false
  }
}

function onTagsChanged(tags: Entry['tags']) {
  emit('updated', { ...props.entry, tags })
}

async function handleDelete() {
  const ok = await confirm({
    title: 'Delete this entry?',
    description: 'This cannot be undone.',
    confirmLabel: 'Delete entry',
    variant: 'destructive',
  })
  if (!ok) return
  deleting.value = true
  try {
    await deleteEntry(props.entry.id)
    toast.success('Entry deleted.')
    emit('deleted', props.entry.id)
  } catch (err) {
    toast.error(err instanceof Error ? err.message : String(err))
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <Card>
    <CardHeader class="flex-row items-start justify-between space-y-0">
      <div class="flex flex-wrap items-center gap-1.5">
        <span v-if="rank != null" class="text-sm font-semibold text-muted-foreground"
          >#{{ rank }}</span
        >
        <Badge variant="secondary">{{ entry.type }}</Badge>
        <Badge variant="secondary">{{ entry.component }}</Badge>
        <Badge variant="outline">{{ entry.status }}</Badge>
        <Tooltip v-if="similarity != null">
          <TooltipTrigger as-child>
            <Badge variant="outline">{{ formatSimilarity(similarity) }} match</Badge>
          </TooltipTrigger>
          <TooltipContent>
            Semantic similarity to your search query — higher percentages mean the entry's meaning
            is closer to what you searched for, not a keyword match.
          </TooltipContent>
        </Tooltip>
        <!-- Read-only mode has no editable TagsPanel below, so show tag
             chips here instead of leaving them off entirely. -->
        <template v-if="readonly">
          <Badge v-for="t in entry.tags || []" :key="t.id" variant="secondary">{{ t.name }}</Badge>
        </template>
      </div>
      <div class="flex items-center gap-2">
        <Button
          type="button"
          variant="ghost"
          size="icon"
          :title="readonly ? 'Open entry' : 'Edit entry'"
          @click="router.push({ name: 'edit-entry', params: { id: entry.id } })"
        >
          <Pencil class="size-4" />
        </Button>
        <Button
          v-if="allowDelete"
          type="button"
          variant="ghost"
          size="icon"
          class="text-destructive hover:text-destructive"
          title="Delete entry"
          :disabled="deleting"
          @click="handleDelete"
        >
          <Trash2 class="size-4" />
        </Button>
        <time class="text-xs text-muted-foreground" :datetime="entry.created_at">
          {{ formatDateTime(entry.created_at) }}
        </time>
      </div>
    </CardHeader>
    <CardContent class="grid gap-3">
      <h3 v-if="entry.title" class="font-semibold">{{ entry.title }}</h3>

      <p class="text-sm text-muted-foreground">
        <span class="font-medium text-foreground">Author</span> {{ entry.author }}
        <template v-if="entry.source">
          · <span class="font-medium text-foreground">Source</span> {{ entry.source }}
        </template>
      </p>

      <MarkdownContent :source="entry.content" :clamped="!expanded" />
      <Button
        v-if="entry.content && entry.content.length > 320"
        type="button"
        variant="link"
        class="h-auto justify-start p-0"
        @click="expanded = !expanded"
      >
        {{ expanded ? 'Show less' : 'Show full content' }}
      </Button>

      <template v-if="!readonly">
        <JiraLinksPanel :entry-id="entry.id" />
        <TagsPanel :entry-id="entry.id" :tags="entry.tags || []" @changed="onTagsChanged" />
      </template>

      <footer v-if="showEditableFooter" class="grid gap-2 border-t pt-3">
        <span class="text-sm font-medium">Update status</span>
        <div class="flex items-center gap-2">
          <Select v-model="patchStatus" :disabled="patching">
            <SelectTrigger size="sm" class="w-40"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem v-for="s in PATCH_STATUSES" :key="s" :value="s">{{ s }}</SelectItem>
            </SelectContent>
          </Select>
          <Button
            type="button"
            size="sm"
            variant="outline"
            :disabled="patching || patchStatus === entry.status"
            @click="applyStatus"
          >
            {{ patching ? 'Saving…' : 'Apply' }}
          </Button>
        </div>
        <p v-if="patchMessage" class="text-xs text-muted-foreground">{{ patchMessage }}</p>
        <p class="text-xs text-muted-foreground">
          <span class="font-medium">ID</span> <code>{{ entry.id }}</code>
        </p>
      </footer>
      <p v-else class="text-xs text-muted-foreground">
        <span class="font-medium">ID</span> <code>{{ entry.id }}</code>
      </p>
    </CardContent>
  </Card>
</template>
