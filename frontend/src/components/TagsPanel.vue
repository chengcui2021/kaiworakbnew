<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { X } from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import { useTagService } from '@/services/useTagService'
import type { Tag } from '@/types/entry'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

const props = defineProps<{
  entryId: string
  tags?: Tag[]
}>()

const emit = defineEmits<{ changed: [tags: Tag[]] }>()

const { listTags, addEntryTag, removeEntryTag } = useTagService()

const localTags = ref<Tag[]>([...(props.tags || [])])
const catalogTags = ref<Tag[]>([])
const newTag = ref('')
const tagging = ref(false)

watch(
  () => props.tags,
  (value) => {
    localTags.value = [...(value || [])]
  }
)

async function loadCatalog() {
  const { tags } = await listTags()
  catalogTags.value = tags
}

async function addTag() {
  const name = newTag.value.trim()
  if (!name) return
  tagging.value = true
  try {
    const tag = await addEntryTag(props.entryId, name)
    newTag.value = ''
    if (!localTags.value.some((t) => t.id === tag.id)) {
      localTags.value = [...localTags.value, tag]
    }
    toast.success(`Tagged with "${tag.name}".`)
    emit('changed', localTags.value)
    await loadCatalog()
  } catch (err) {
    toast.error(err instanceof Error ? err.message : 'Tag failed')
  } finally {
    tagging.value = false
  }
}

async function removeTag(tagId: string) {
  try {
    await removeEntryTag(props.entryId, tagId)
    localTags.value = localTags.value.filter((t) => t.id !== tagId)
    toast.success('Tag removed.')
    emit('changed', localTags.value)
  } catch (err) {
    toast.error(err instanceof Error ? err.message : 'Remove failed')
  }
}

onMounted(loadCatalog)
</script>

<template>
  <section class="grid gap-2">
    <h3 class="text-sm font-semibold">Tags</h3>

    <div v-if="localTags.length" class="flex flex-wrap gap-1.5">
      <Badge v-for="tag in localTags" :key="tag.id" variant="secondary" class="gap-1">
        {{ tag.name }}
        <button
          type="button"
          aria-label="Remove tag"
          class="opacity-70 hover:opacity-100"
          @click="removeTag(tag.id)"
        >
          <X class="size-3" aria-hidden="true" />
        </button>
      </Badge>
    </div>
    <p v-else class="text-sm text-muted-foreground">No tags yet.</p>

    <div class="flex items-center gap-2">
      <Input
        v-model="newTag"
        type="text"
        list="tag-catalog"
        placeholder="e.g. api, onboarding"
        :disabled="tagging"
        class="h-8 w-48"
        @keyup.enter="addTag"
      />
      <datalist id="tag-catalog">
        <option v-for="tag in catalogTags" :key="tag.id" :value="tag.name" />
      </datalist>
      <Button
        type="button"
        size="sm"
        variant="outline"
        :disabled="tagging || !newTag.trim()"
        @click="addTag"
      >
        {{ tagging ? 'Adding…' : 'Add tag' }}
      </Button>
    </div>
  </section>
</template>
