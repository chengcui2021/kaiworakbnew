<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { AlertCircle, ExternalLink } from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import { useJiraLinkService } from '@/services/useJiraLinkService'
import type { JiraLink } from '@/types/entry'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

const props = defineProps<{ entryId: string }>()

const { listJiraLinks, addJiraLink, removeJiraLink } = useJiraLinkService()

const links = ref<JiraLink[]>([])
const loading = ref(false)
const linking = ref(false)
const newKey = ref('')
const loadError = ref('')

async function loadLinks() {
  loading.value = true
  loadError.value = ''
  try {
    const data = await listJiraLinks(props.entryId)
    links.value = data.links
  } catch (err) {
    loadError.value = err instanceof Error ? err.message : 'Failed to load Jira links'
  } finally {
    loading.value = false
  }
}

async function addLink() {
  const key = newKey.value.trim()
  if (!key) return
  linking.value = true
  try {
    const link = await addJiraLink(props.entryId, key)
    newKey.value = ''
    toast.success(`Linked ${link.jira_key}.`)
    await loadLinks()
  } catch (err) {
    toast.error(err instanceof Error ? err.message : 'Link failed')
  } finally {
    linking.value = false
  }
}

async function removeLink(jiraKey: string) {
  try {
    await removeJiraLink(props.entryId, jiraKey)
    toast.success(`Removed ${jiraKey}.`)
    await loadLinks()
  } catch (err) {
    toast.error(err instanceof Error ? err.message : 'Remove failed')
  }
}

onMounted(loadLinks)
</script>

<template>
  <section class="grid gap-2">
    <h3 class="text-sm font-semibold">Jira links</h3>

    <div class="flex items-center gap-2">
      <Input
        v-model="newKey"
        type="text"
        placeholder="e.g. PROJ-123"
        :disabled="linking"
        class="h-8 w-40"
        @keyup.enter="addLink"
      />
      <Button
        type="button"
        size="sm"
        variant="outline"
        :disabled="linking || !newKey.trim()"
        @click="addLink"
      >
        {{ linking ? 'Linking…' : 'Link' }}
      </Button>
    </div>

    <p v-if="loading" class="text-sm text-muted-foreground">Loading Jira links…</p>
    <Alert v-else-if="loadError" variant="destructive" role="alert">
      <AlertCircle class="size-4" aria-hidden="true" />
      <AlertTitle>Couldn't load Jira links</AlertTitle>
      <AlertDescription>{{ loadError }}</AlertDescription>
    </Alert>
    <p v-else-if="!links.length" class="text-sm text-muted-foreground">
      No Jira tickets linked yet.
    </p>

    <ul v-else class="grid gap-3">
      <li v-for="link in links" :key="link.jira_key" class="rounded-md border p-3">
        <div class="flex items-center justify-between gap-2">
          <a
            v-if="link.browse_url"
            class="inline-flex items-center gap-1 text-sm font-medium underline"
            :href="link.browse_url"
            target="_blank"
            rel="noopener noreferrer"
          >
            {{ link.jira_key }}
            <ExternalLink class="size-3.5" aria-hidden="true" />
          </a>
          <span v-else class="text-sm font-medium">{{ link.jira_key }}</span>
          <Button type="button" variant="ghost" size="sm" @click="removeLink(link.jira_key)"
            >Remove</Button
          >
        </div>
        <p v-if="link.title" class="mt-1 text-sm">{{ link.title }}</p>
        <p v-if="link.status || link.issue_type" class="mt-1 flex flex-wrap gap-1.5">
          <Badge v-if="link.issue_type" variant="secondary">{{ link.issue_type }}</Badge>
          <Badge v-if="link.status" variant="outline">{{ link.status }}</Badge>
          <Badge v-if="link.story_points != null" variant="outline"
            >{{ link.story_points }} pts</Badge
          >
        </p>
        <p v-if="link.enrichment_error" class="mt-1 text-xs text-destructive">
          {{ link.enrichment_error }}
        </p>
        <ul v-if="link.is_epic && link.child_issues?.length" class="mt-2 ml-4 list-disc text-sm">
          <li v-for="child in link.child_issues" :key="child.key">
            <a
              :href="child.browse_url"
              target="_blank"
              rel="noopener noreferrer"
              class="underline"
              >{{ child.key }}</a
            >
            — {{ child.title }}
            <span class="text-xs text-muted-foreground">
              ({{ child.status
              }}<template v-if="child.story_points != null">
                · {{ child.story_points }} pts</template
              >)
            </span>
          </li>
        </ul>
      </li>
    </ul>
  </section>
</template>
