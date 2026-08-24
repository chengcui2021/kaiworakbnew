<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { FileCode, Loader2, Type, Upload, X } from 'lucide-vue-next'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { useEntryService } from '@/services/useEntryService'
import { useTransformService } from '@/services/useTransformService'
import { useTemplateService } from '@/services/useTemplateService'
import { useJiraLinkService } from '@/services/useJiraLinkService'
import { useTagService } from '@/services/useTagService'
import { useWorkstream } from '@/composables/useWorkstream'
import type { Tag, Template } from '@/types/entry'
import { readMarkdownFile, isPdfFilename, validateTransformFile } from '@/utils/markdownUpload'
import { useUnsavedChangesGuard } from '@/composables/useUnsavedChangesGuard'
import { useConfirm } from '@/composables/useConfirm'
import { submitEntrySchema, type SubmitEntryFormValues } from '@/schemas/entrySchema'
import MarkdownContent from '@/components/MarkdownContent.vue'
import MarkdownSplitEditor from '@/components/MarkdownSplitEditor.vue'
import TiptapMarkdownEditor from '@/components/TiptapMarkdownEditor.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent } from '@/components/ui/card'
import { FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

const router = useRouter()
const { createEntry } = useEntryService()
const { transformText, transformPdf } = useTransformService()
const { listTemplates } = useTemplateService()
const { addJiraLink } = useJiraLinkService()
const { listTags, addEntryTag } = useTagService()
const { confirm } = useConfirm()
const { activeWorkstream } = useWorkstream()

const dbTemplates = ref<Template[]>([])

// Associations — collected locally, linked after entry creation
const jiraKeys = ref<string[]>([])
const newJiraKey = ref('')
const tagNames = ref<string[]>([])
const newTagName = ref('')
const catalogTags = ref<Tag[]>([])

const { handleSubmit, values, resetForm, meta, setFieldValue } = useForm<SubmitEntryFormValues>({
  validationSchema: toTypedSchema(submitEntrySchema),
  initialValues: {
    title: '',
    content: '',
    author: '',
  },
})

useUnsavedChangesGuard(() => meta.value.dirty)

const submitting = ref(false)
const uploading = ref(false)
const contentMode = ref<'write' | 'split' | 'preview'>('split')
const richTextMode = ref<'rich' | 'markdown'>('rich')
const fileInputRef = ref<HTMLInputElement | null>(null)
const selectedTemplate = ref('')

// Transform state
const transformFile = ref<File | null>(null)
const transformFileName = ref('')
const transforming = ref(false)
const transformFileInputRef = ref<HTMLInputElement | null>(null)
const canTransform = computed(() => transformFile.value !== null && selectedTemplate.value !== '')

function openFilePicker() {
  fileInputRef.value?.click()
}

async function loadTemplates() {
  try {
    const data = await listTemplates()
    dbTemplates.value = data.templates
  } catch {
    // Silently fall back to empty list — template selector will just be empty
  }
}

async function onTemplateSelected(value: unknown) {
  if (typeof value !== 'string' || !value) return
  const template = dbTemplates.value.find((t) => t.id === value)
  if (!template) return

  if (values.content?.trim()) {
    const ok = await confirm({
      title: 'Replace current content?',
      description: `Loading the "${template.name}" template will overwrite what you've written in Content. This cannot be undone.`,
      confirmLabel: 'Load template',
      variant: 'destructive',
    })
    if (!ok) return
  }

  setFieldValue('content', template.content)
  contentMode.value = 'split'
  selectedTemplate.value = value
}

async function onMarkdownFileSelected(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  uploading.value = true
  try {
    const text = await readMarkdownFile(file)
    setFieldValue('content', text)
    selectedTemplate.value = ''
    if (!values.title?.trim()) {
      setFieldValue(
        'title',
        file.name
          .replace(/\.(md|markdown|mdown|mkd)$/i, '')
          .replace(/[-_]+/g, ' ')
          .trim()
      )
    }
    contentMode.value = 'split'
    toast.success(`${file.name} loaded`, {
      description: 'Review the preview, then submit.',
    })
  } catch (err) {
    setFieldValue('content', '')
    contentMode.value = 'write'
    toast.error(err instanceof Error ? err.message : 'Could not load the Markdown file.')
  } finally {
    uploading.value = false
    input.value = ''
  }
}

function openTransformFilePicker() {
  transformFileInputRef.value?.click()
}

function onTransformFileSelected(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  const error = validateTransformFile(file)
  if (error) {
    toast.error(error)
    input.value = ''
    return
  }

  transformFile.value = file
  transformFileName.value = file.name
  input.value = ''
}

function removeTransformFile() {
  transformFile.value = null
  transformFileName.value = ''
}

async function onTransform() {
  if (!transformFile.value || !selectedTemplate.value) return
  const template = dbTemplates.value.find((t) => t.id === selectedTemplate.value)
  if (!template) return

  if (values.content?.trim()) {
    const ok = await confirm({
      title: 'Replace current content?',
      description:
        "Transforming the document will overwrite what you've written in Content. This cannot be undone.",
      confirmLabel: 'Transform',
      variant: 'destructive',
    })
    if (!ok) return
  }

  transforming.value = true
  try {
    let result: { content: string }
    if (isPdfFilename(transformFile.value.name)) {
      result = await transformPdf(transformFile.value, template.content)
    } else {
      const text = await readMarkdownFile(transformFile.value)
      result = await transformText(text, template.content)
    }
    setFieldValue('content', result.content)
    contentMode.value = 'split'
    toast.success('Document transformed', {
      description: 'Review the result, then submit.',
    })
  } catch (err) {
    toast.error(err instanceof Error ? err.message : 'Transform failed. Try again.')
  } finally {
    transforming.value = false
  }
}

function addJiraKey() {
  const key = newJiraKey.value.trim()
  if (!key || jiraKeys.value.includes(key)) return
  jiraKeys.value.push(key)
  newJiraKey.value = ''
}

function removeJiraKey(index: number) {
  jiraKeys.value.splice(index, 1)
}

function addTagName() {
  const name = newTagName.value.trim()
  if (!name || tagNames.value.includes(name)) return
  tagNames.value.push(name)
  newTagName.value = ''
}

function removeTagName(index: number) {
  tagNames.value.splice(index, 1)
}

async function loadCatalogTags() {
  try {
    const { tags } = await listTags()
    catalogTags.value = tags
  } catch {
    // Silently ignore — autocomplete just won't have suggestions
  }
}

const onSubmit = handleSubmit(async (formValues) => {
  submitting.value = true
  try {
    const entry = await createEntry({
      type: 'documentation',
      component: 'api',
      title: formValues.title,
      content: formValues.content,
      author: formValues.author,
      workstream_id: activeWorkstream.value?.id ?? null,
    })

    // Associate Jira links and tags (best-effort — entry already exists)
    const linkPromises = jiraKeys.value.map((key) => addJiraLink(entry.id, key))
    const tagPromises = tagNames.value.map((name) => addEntryTag(entry.id, name))
    const results = await Promise.allSettled([...linkPromises, ...tagPromises])
    const failures = results.filter((r) => r.status === 'rejected')

    if (failures.length) {
      toast.warning('Entry created, but some associations failed', {
        description: `${failures.length} link/tag association(s) could not be saved.`,
        action: {
          label: 'View entry',
          onClick: () => router.push({ name: 'edit-entry', params: { id: entry.id } }),
        },
      })
    } else {
      toast.success('Entry created', {
        description: 'Saved successfully.',
        action: {
          label: 'View entry',
          onClick: () => router.push({ name: 'edit-entry', params: { id: entry.id } }),
        },
      })
    }

    resetForm()
    contentMode.value = 'write'
    selectedTemplate.value = ''
    jiraKeys.value = []
    newJiraKey.value = ''
    tagNames.value = []
    newTagName.value = ''
    if (fileInputRef.value) fileInputRef.value.value = ''
  } catch (err) {
    toast.error(err instanceof Error ? err.message : 'Submission failed')
  } finally {
    submitting.value = false
  }
})

onMounted(() => {
  loadTemplates()
  loadCatalogTags()
})
</script>

<template>
  <div class="flex flex-col gap-6">
    <div>
      <h2 class="text-2xl font-semibold">Submit entry</h2>
      <p class="mt-1 text-muted-foreground">Add institutional knowledge for semantic search.</p>
    </div>

    <Card>
      <CardContent class="pt-6">
        <form class="grid gap-6" @submit="onSubmit">
          <section class="grid gap-4">
            <span class="text-sm font-semibold">Entry details</span>
            <FormField v-slot="{ componentField }" name="title">
              <FormItem>
                <FormLabel>Title</FormLabel>
                <FormControl>
                  <Input
                    type="text"
                    maxlength="255"
                    placeholder="Short summary of this entry"
                    v-bind="componentField"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            </FormField>
            <div class="grid gap-2">
              <Label for="document-template">Start from a template</Label>
              <div class="flex flex-wrap items-center gap-3">
                <Select :model-value="selectedTemplate" @update:model-value="onTemplateSelected">
                  <SelectTrigger id="document-template" class="w-full sm:w-72">
                    <SelectValue placeholder="Choose a document template…" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem v-for="t in dbTemplates" :key="t.id" :value="t.id">{{
                      t.name
                    }}</SelectItem>
                  </SelectContent>
                </Select>
                <span class="text-sm text-muted-foreground">or</span>
                <input
                  ref="fileInputRef"
                  type="file"
                  class="hidden"
                  accept=".md,.markdown,.mdown,.mkd,text/markdown"
                  @change="onMarkdownFileSelected"
                />
                <Button
                  type="button"
                  size="sm"
                  :disabled="uploading || submitting"
                  @click="openFilePicker"
                >
                  {{ uploading ? 'Loading…' : 'Upload' }}
                </Button>
              </div>

              <!-- Document transform section — visible when a template is selected -->
              <div
                v-if="selectedTemplate"
                class="mt-3 rounded-md border border-dashed border-muted-foreground/30 p-4"
              >
                <span class="text-sm font-medium">Transform a document to this template</span>
                <p class="mt-1 text-xs text-muted-foreground">
                  Upload a .md or .pdf file and the LLM will restructure it to match the selected
                  template.
                </p>

                <div class="mt-3 flex flex-wrap items-center gap-3">
                  <input
                    ref="transformFileInputRef"
                    type="file"
                    class="hidden"
                    accept=".md,.markdown,.mdown,.mkd,.pdf,text/markdown,application/pdf"
                    @change="onTransformFileSelected"
                  />

                  <template v-if="!transformFileName">
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      :disabled="transforming || submitting"
                      @click="openTransformFilePicker"
                    >
                      <Upload class="mr-1.5 h-4 w-4" />
                      Choose file
                    </Button>
                  </template>
                  <template v-else>
                    <span
                      class="inline-flex items-center gap-1.5 rounded-md bg-muted px-2.5 py-1 text-sm"
                    >
                      {{ transformFileName }}
                      <button
                        type="button"
                        class="text-muted-foreground hover:text-foreground"
                        :disabled="transforming"
                        @click="removeTransformFile"
                      >
                        <X class="h-3.5 w-3.5" />
                      </button>
                    </span>
                  </template>

                  <Button
                    v-if="canTransform"
                    type="button"
                    size="sm"
                    :disabled="transforming || submitting"
                    @click="onTransform"
                  >
                    <Loader2 v-if="transforming" class="mr-1.5 h-4 w-4 animate-spin" />
                    {{ transforming ? 'Transforming…' : 'Transform' }}
                  </Button>
                </div>
              </div>
            </div>
            <FormField v-slot="{ componentField }" name="content">
              <FormItem>
                <FormLabel>Content</FormLabel>
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
                        placeholder="Write your entry: headings, lists, bold, links…"
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
            <FormField v-slot="{ componentField }" name="author">
              <FormItem>
                <FormLabel>Author</FormLabel>
                <FormControl>
                  <Input
                    type="text"
                    maxlength="255"
                    placeholder="Your name"
                    v-bind="componentField"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            </FormField>
          </section>

          <section class="grid gap-4">
            <span class="text-sm font-semibold">Associations</span>
            <div class="grid grid-cols-2 gap-4">
              <div class="grid gap-2">
                <Label>Jira links</Label>
                <div class="flex items-center gap-2">
                  <Input
                    v-model="newJiraKey"
                    type="text"
                    placeholder="e.g. PROJ-123"
                    :disabled="submitting"
                    class="w-full"
                    @keyup.enter="addJiraKey"
                  />
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    :disabled="!newJiraKey.trim() || submitting"
                    @click="addJiraKey"
                  >
                    Add
                  </Button>
                </div>
                <div v-if="jiraKeys.length" class="flex flex-wrap gap-1.5">
                  <Badge v-for="(key, i) in jiraKeys" :key="key" variant="secondary" class="gap-1">
                    {{ key }}
                    <button
                      type="button"
                      aria-label="Remove Jira link"
                      class="opacity-70 hover:opacity-100"
                      @click="removeJiraKey(i)"
                    >
                      <X class="size-3" aria-hidden="true" />
                    </button>
                  </Badge>
                </div>
              </div>

              <div class="grid gap-2">
                <Label>Tags</Label>
                <div class="flex items-center gap-2">
                  <Input
                    v-model="newTagName"
                    type="text"
                    list="submit-tag-catalog"
                    placeholder="e.g. api, onboarding"
                    :disabled="submitting"
                    class="w-full"
                    @keyup.enter="addTagName"
                  />
                  <datalist id="submit-tag-catalog">
                    <option v-for="tag in catalogTags" :key="tag.id" :value="tag.name" />
                  </datalist>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    :disabled="!newTagName.trim() || submitting"
                    @click="addTagName"
                  >
                    Add
                  </Button>
                </div>
                <div v-if="tagNames.length" class="flex flex-wrap gap-1.5">
                  <Badge
                    v-for="(name, i) in tagNames"
                    :key="name"
                    variant="secondary"
                    class="gap-1"
                  >
                    {{ name }}
                    <button
                      type="button"
                      aria-label="Remove tag"
                      class="opacity-70 hover:opacity-100"
                      @click="removeTagName(i)"
                    >
                      <X class="size-3" aria-hidden="true" />
                    </button>
                  </Badge>
                </div>
              </div>
            </div>
          </section>

          <div>
            <Button type="submit" :disabled="submitting">
              {{ submitting ? 'Submitting…' : 'Submit entry' }}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  </div>
</template>
