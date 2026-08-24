<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { FileCode, Type } from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { useTemplateService } from '@/services/useTemplateService'
import { useUnsavedChangesGuard } from '@/composables/useUnsavedChangesGuard'
import { templateSchema, type TemplateFormValues } from '@/schemas/templateSchema'
import MarkdownContent from '@/components/MarkdownContent.vue'
import MarkdownSplitEditor from '@/components/MarkdownSplitEditor.vue'
import TiptapMarkdownEditor from '@/components/TiptapMarkdownEditor.vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'

const router = useRouter()
const { createTemplate } = useTemplateService()

const { handleSubmit, values, resetForm, meta } = useForm<TemplateFormValues>({
  validationSchema: toTypedSchema(templateSchema),
  initialValues: {
    name: '',
    content: '',
  },
})

useUnsavedChangesGuard(() => meta.value.dirty)

const saving = ref(false)
const contentMode = ref<'write' | 'split' | 'preview'>('split')
const richTextMode = ref<'rich' | 'markdown'>('rich')

const saveTemplate = handleSubmit(async (formValues) => {
  saving.value = true
  try {
    await createTemplate({
      name: formValues.name,
      content: formValues.content,
    })
    resetForm({ values: formValues })
    toast.success('Template created.')
    router.push('/templates')
  } catch (err) {
    toast.error(err instanceof Error ? err.message : String(err))
  } finally {
    saving.value = false
  }
})

function goBack() {
  router.push('/templates')
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div>
        <h2 class="text-2xl font-semibold">Create template</h2>
        <p class="mt-1 text-muted-foreground">
          Add a new document template with a name and markdown content.
        </p>
      </div>
      <div class="flex gap-2">
        <Button type="button" variant="outline" :disabled="saving" @click="goBack"> Cancel </Button>
        <Button type="button" :disabled="saving" @click="saveTemplate">
          {{ saving ? 'Saving...' : 'Save template' }}
        </Button>
      </div>
    </div>

    <form class="flex flex-col gap-6" @submit="saveTemplate">
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
