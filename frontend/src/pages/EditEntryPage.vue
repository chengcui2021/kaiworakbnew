<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { AlertCircle, Download, FileCode, SlidersHorizontal, Type } from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { useEntryService } from '@/services/useEntryService'
import { PATCH_STATUSES, PUBLISH_STATUSES } from '@/constants/entryOptions'
import { useConfirm } from '@/composables/useConfirm'
import { useUnsavedChangesGuard } from '@/composables/useUnsavedChangesGuard'
import { editEntrySchema, type EditEntryFormValues } from '@/schemas/entrySchema'
import type { ComponentName, EntryStatus, EntryType, Tag } from '@/types/entry'

// Original classification values — preserved from the loaded entry, not user-editable
const origClassification = ref({
  type: 'documentation' as string,
  component: 'api' as string,
  source: '',
})
import JiraLinksPanel from '@/components/JiraLinksPanel.vue'
import MarkdownContent from '@/components/MarkdownContent.vue'
import MarkdownSplitEditor from '@/components/MarkdownSplitEditor.vue'
import TagsPanel from '@/components/TagsPanel.vue'
import TiptapMarkdownEditor from '@/components/TiptapMarkdownEditor.vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Separator } from '@/components/ui/separator'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'
import { FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

const props = defineProps<{ id: string }>()

const router = useRouter()
const { getEntry, updateEntry, deleteEntry } = useEntryService()
const { confirm } = useConfirm()

const { handleSubmit, values, resetForm, meta } = useForm<EditEntryFormValues>({
  validationSchema: toTypedSchema(editEntrySchema),
  initialValues: {
    title: '',
    content: '',
    author: '',
    status: 'open',
  },
})

useUnsavedChangesGuard(() => meta.value.dirty)

const loading = ref(true)
const saving = ref(false)
const deleting = ref(false)
const contentMode = ref<'write' | 'split' | 'preview'>('split')
const richTextMode = ref<'rich' | 'markdown'>('rich')
const classificationOpen = ref(false)
const notFound = ref(false)
const loadError = ref('')
const entryTags = ref<Tag[]>([])

async function loadEntry() {
  loading.value = true
  try {
    const entry = await getEntry(props.id)
    entryTags.value = entry.tags
    origClassification.value = {
      type: entry.type,
      component: entry.component,
      source: entry.source || '',
    }
    resetForm({
      values: {
        title: entry.title,
        content: entry.content,
        author: entry.author,
        status: entry.status,
      },
    })
  } catch (err) {
    if (err instanceof Error && err.message.toLowerCase().includes('not found')) {
      notFound.value = true
    } else {
      loadError.value = err instanceof Error ? err.message : String(err)
    }
  } finally {
    loading.value = false
  }
}

const saveChanges = handleSubmit(async (formValues) => {
  saving.value = true
  try {
    await updateEntry(props.id, {
      type: origClassification.value.type as EntryType,
      component: origClassification.value.component as ComponentName,
      title: formValues.title,
      content: formValues.content,
      source: origClassification.value.source?.trim() || null,
      author: formValues.author,
      status: formValues.status as EntryStatus,
    })
    resetForm({ values: formValues })
    toast.success('Changes saved.')
    router.push('/browse')
  } catch (err) {
    toast.error(err instanceof Error ? err.message : String(err))
  } finally {
    saving.value = false
  }
})

async function handleDeleteEntry() {
  const ok = await confirm({
    title: 'Delete this entry?',
    description: 'This cannot be undone.',
    confirmLabel: 'Delete entry',
    variant: 'destructive',
  })
  if (!ok) return
  deleting.value = true
  try {
    await deleteEntry(props.id)
    resetForm({ values })
    toast.success('Entry deleted.')
    router.push('/browse')
  } catch (err) {
    toast.error(err instanceof Error ? err.message : String(err))
  } finally {
    deleting.value = false
  }
}

function onTagsChanged(tags: Tag[]) {
  entryTags.value = tags
}

function downloadMarkdown() {
  const content = values.content || ''
  const title = values.title || 'untitled'
  const blob = new Blob([content], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${title}.md`
  a.click()
  URL.revokeObjectURL(url)
}

function goBack() {
  router.back()
}

onMounted(loadEntry)
</script>

<template>
  <div class="flex flex-col gap-6">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div>
        <h2 class="text-2xl font-semibold">Edit entry</h2>
        <p class="mt-1 text-muted-foreground">
          Modify the content and properties of this knowledge base entry.
        </p>
      </div>
      <div v-if="!loading && !notFound && !loadError" class="flex gap-2">
        <Button
          type="button"
          variant="destructive"
          data-test="edit-top-delete"
          :disabled="saving || deleting"
          @click="handleDeleteEntry"
        >
          {{ deleting ? 'Deleting...' : 'Delete entry' }}
        </Button>
        <Button
          type="button"
          variant="outline"
          data-test="edit-top-download"
          :disabled="saving || deleting || !values.content?.trim()"
          @click="downloadMarkdown"
        >
          <Download class="mr-1.5 h-4 w-4" />
          Download
        </Button>
        <Button
          type="button"
          variant="outline"
          data-test="edit-top-cancel"
          :disabled="saving || deleting"
          @click="goBack"
        >
          Cancel
        </Button>
        <Button
          type="button"
          data-test="edit-top-save"
          :disabled="saving || deleting"
          @click="saveChanges"
        >
          {{ saving ? 'Saving...' : 'Save Changes' }}
        </Button>
      </div>
    </div>

    <Card v-if="loading">
      <CardContent class="pt-6">
        <p class="text-sm text-muted-foreground">Loading entry...</p>
      </CardContent>
    </Card>

    <Card v-else-if="notFound">
      <CardContent class="grid gap-3 pt-6">
        <p>Entry not found. It may have been deleted.</p>
        <Button type="button" variant="outline" class="w-fit" @click="router.push('/browse')"
          >Back to Browse</Button
        >
      </CardContent>
    </Card>

    <Card v-else-if="loadError">
      <CardContent class="grid gap-3 pt-6">
        <Alert variant="destructive" role="alert">
          <AlertCircle class="size-4" aria-hidden="true" />
          <AlertTitle>Couldn't load entry</AlertTitle>
          <AlertDescription>{{ loadError }}</AlertDescription>
        </Alert>
        <Button type="button" variant="outline" class="w-fit" @click="router.push('/browse')"
          >Back to Browse</Button
        >
      </CardContent>
    </Card>

    <form v-else class="flex flex-col gap-6" @submit="saveChanges">
      <Card>
        <CardHeader class="flex-row items-center justify-between">
          <CardTitle>Content</CardTitle>
          <Sheet v-model:open="classificationOpen" :modal="false">
            <SheetTrigger as-child>
              <Button type="button" variant="outline">
                <SlidersHorizontal />
                Properties
              </Button>
            </SheetTrigger>
            <SheetContent class="w-full sm:max-w-md">
              <SheetHeader>
                <SheetTitle>Properties</SheetTitle>
                <SheetDescription>Author, status, links, and tags for this entry.</SheetDescription>
              </SheetHeader>
              <div class="grid flex-1 gap-6 overflow-y-auto px-4 pb-6">
                <section class="grid gap-4">
                  <FormField v-slot="{ componentField }" name="title">
                    <FormItem>
                      <FormLabel>Title</FormLabel>
                      <FormControl>
                        <Input type="text" maxlength="255" v-bind="componentField" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  </FormField>
                  <FormField v-slot="{ componentField }" name="author">
                    <FormItem>
                      <FormLabel>Author</FormLabel>
                      <FormControl>
                        <Input type="text" maxlength="255" v-bind="componentField" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  </FormField>
                  <FormField v-slot="{ componentField }" name="status">
                    <FormItem>
                      <FormLabel>Status</FormLabel>
                      <Select v-bind="componentField">
                        <FormControl>
                          <SelectTrigger><SelectValue /></SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectGroup>
                            <SelectLabel>Lifecycle</SelectLabel>
                            <SelectItem v-for="s in PATCH_STATUSES" :key="s" :value="s">{{
                              s
                            }}</SelectItem>
                          </SelectGroup>
                          <SelectGroup>
                            <SelectLabel>Publish</SelectLabel>
                            <SelectItem v-for="s in PUBLISH_STATUSES" :key="s" :value="s">{{
                              s
                            }}</SelectItem>
                          </SelectGroup>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  </FormField>
                </section>

                <Separator />

                <section class="grid gap-4">
                  <h3 class="font-semibold">Links &amp; Tags</h3>
                  <JiraLinksPanel :entry-id="id" />
                  <TagsPanel :entry-id="id" :tags="entryTags" @changed="onTagsChanged" />
                </section>
              </div>
              <SheetFooter>
                <Button type="button" :disabled="saving || deleting" @click="saveChanges">
                  {{ saving ? 'Saving...' : 'Save Changes' }}
                </Button>
              </SheetFooter>
            </SheetContent>
          </Sheet>
        </CardHeader>
        <CardContent class="grid gap-3">
          <FormField v-slot="{ componentField }" name="content">
            <FormItem>
              <FormLabel class="sr-only">Content</FormLabel>
              <MarkdownSplitEditor v-model="contentMode">
                <template #actions>
                  <Button
                    type="button"
                    size="sm"
                    :variant="richTextMode === 'rich' ? 'secondary' : 'ghost'"
                    @click="richTextMode = 'rich'"
                  >
                    <Type />
                    Rich text
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    :variant="richTextMode === 'markdown' ? 'secondary' : 'ghost'"
                    @click="richTextMode = 'markdown'"
                  >
                    <FileCode />
                    Markdown
                  </Button>
                </template>
                <template #write="{ toolbarTarget }">
                  <FormControl>
                    <TiptapMarkdownEditor
                      aria-label="Content"
                      :mode="richTextMode"
                      :toolbar-target="toolbarTarget"
                      v-bind="componentField"
                    />
                  </FormControl>
                </template>
                <template #preview>
                  <Card class="relative rounded-none border-0 shadow-none">
                    <span
                      class="absolute top-0 right-0 rounded-bl-md bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground"
                      >Preview</span
                    >
                    <CardContent class="pt-6">
                      <MarkdownContent v-if="values.content?.trim()" :source="values.content" />
                      <p v-else class="text-sm text-muted-foreground">Nothing to preview yet.</p>
                    </CardContent>
                  </Card>
                </template>
              </MarkdownSplitEditor>
              <FormMessage />
            </FormItem>
          </FormField>
        </CardContent>
      </Card>
    </form>
  </div>
</template>
