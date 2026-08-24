<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { AlertCircle, FileCode, Type } from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { useTemplateService } from '@/services/useTemplateService'
import { useConfirm } from '@/composables/useConfirm'
import { useUnsavedChangesGuard } from '@/composables/useUnsavedChangesGuard'
import { templateSchema, type TemplateFormValues } from '@/schemas/templateSchema'
import MarkdownContent from '@/components/MarkdownContent.vue'
import MarkdownSplitEditor from '@/components/MarkdownSplitEditor.vue'
import TiptapMarkdownEditor from '@/components/TiptapMarkdownEditor.vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'

const props = defineProps<{ id: string }>()

const router = useRouter()
const { getTemplate, updateTemplate, deleteTemplate } = useTemplateService()
const { confirm } = useConfirm()

const { handleSubmit, values, resetForm, meta } = useForm<TemplateFormValues>({
  validationSchema: toTypedSchema(templateSchema),
  initialValues: {
    name: '',
    content: '',
  },
})

useUnsavedChangesGuard(() => meta.value.dirty)

const loading = ref(true)
const saving = ref(false)
const deleting = ref(false)
const contentMode = ref<'write' | 'split' | 'preview'>('split')
const richTextMode = ref<'rich' | 'markdown'>('rich')
const notFound = ref(false)
const loadError = ref('')

async function loadTemplate() {
  loading.value = true
  try {
    const tpl = await getTemplate(props.id)
    resetForm({
      values: {
        name: tpl.name,
        content: tpl.content,
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
    await updateTemplate(props.id, {
      name: formValues.name,
      content: formValues.content,
    })
    resetForm({ values: formValues })
    toast.success('Template saved.')
    router.push('/templates')
  } catch (err) {
    toast.error(err instanceof Error ? err.message : String(err))
  } finally {
    saving.value = false
  }
})

async function handleDeleteTemplate() {
  const ok = await confirm({
    title: 'Delete this template?',
    description: 'This cannot be undone.',
    confirmLabel: 'Delete template',
    variant: 'destructive',
  })
  if (!ok) return
  deleting.value = true
  try {
    await deleteTemplate(props.id)
    resetForm({ values })
    toast.success('Template deleted.')
    router.push('/templates')
  } catch (err) {
    toast.error(err instanceof Error ? err.message : String(err))
  } finally {
    deleting.value = false
  }
}

function goBack() {
  router.back()
}

onMounted(loadTemplate)
</script>

<template>
  <div class="flex flex-col gap-6">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div>
        <h2 class="text-2xl font-semibold">Edit template</h2>
        <p class="mt-1 text-muted-foreground">
          Modify the name and content of this document template.
        </p>
      </div>
      <div v-if="!loading && !notFound && !loadError" class="flex gap-2">
        <Button
          type="button"
          variant="destructive"
          data-test="template-top-delete"
          :disabled="saving || deleting"
          @click="handleDeleteTemplate"
        >
          {{ deleting ? 'Deleting...' : 'Delete template' }}
        </Button>
        <Button
          type="button"
          variant="outline"
          data-test="template-top-cancel"
          :disabled="saving || deleting"
          @click="goBack"
        >
          Cancel
        </Button>
        <Button
          type="button"
          data-test="template-top-save"
          :disabled="saving || deleting"
          @click="saveChanges"
        >
          {{ saving ? 'Saving...' : 'Save Changes' }}
        </Button>
      </div>
    </div>

    <Card v-if="loading">
      <CardContent class="pt-6">
        <p class="text-sm text-muted-foreground">Loading template...</p>
      </CardContent>
    </Card>

    <Card v-else-if="notFound">
      <CardContent class="grid gap-3 pt-6">
        <p>Template not found. It may have been deleted.</p>
        <Button type="button" variant="outline" class="w-fit" @click="router.push('/templates')">
          Back to Templates
        </Button>
      </CardContent>
    </Card>

    <Card v-else-if="loadError">
      <CardContent class="grid gap-3 pt-6">
        <Alert variant="destructive" role="alert">
          <AlertCircle class="size-4" aria-hidden="true" />
          <AlertTitle>Couldn't load template</AlertTitle>
          <AlertDescription>{{ loadError }}</AlertDescription>
        </Alert>
        <Button type="button" variant="outline" class="w-fit" @click="router.push('/templates')">
          Back to Templates
        </Button>
      </CardContent>
    </Card>

    <form v-else class="flex flex-col gap-6" @submit="saveChanges">
      <Card>
        <CardHeader>
          <CardTitle>Details</CardTitle>
        </CardHeader>
        <CardContent class="grid gap-4">
          <FormField v-slot="{ componentField }" name="name">
            <FormItem>
              <FormLabel>Name</FormLabel>
              <FormControl>
                <Input type="text" maxlength="255" v-bind="componentField" />
              </FormControl>
              <FormMessage />
            </FormItem>
          </FormField>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Content</CardTitle>
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
                    >
                      Preview
                    </span>
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
