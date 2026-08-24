<script setup lang="ts">
import { h, onMounted, ref } from 'vue'
import {
  FlexRender,
  getCoreRowModel,
  getSortedRowModel,
  useVueTable,
  type ColumnDef,
  type SortingState,
} from '@tanstack/vue-table'
import { AlertCircle, ArrowUpDown } from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import { useTagService } from '@/services/useTagService'
import { useEntryService } from '@/services/useEntryService'
import { useConfirm } from '@/composables/useConfirm'
import type { Tag } from '@/types/entry'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

const { listTags, createTag, updateTag, deleteTag } = useTagService()
const { listEntries } = useEntryService()
const { confirm } = useConfirm()

const tags = ref<Tag[]>([])
const loading = ref(false)
const saving = ref(false)
const newName = ref('')
const editId = ref('')
const editName = ref('')
const loadError = ref('')

async function loadTags() {
  loading.value = true
  loadError.value = ''
  try {
    const data = await listTags()
    tags.value = data.tags
  } catch (err) {
    loadError.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

async function handleCreateTag() {
  const name = newName.value.trim()
  if (!name) return
  saving.value = true
  try {
    const tag = await createTag(name)
    newName.value = ''
    toast.success(`Added "${tag.name}".`)
    await loadTags()
  } catch (err) {
    toast.error(err instanceof Error ? err.message : String(err))
  } finally {
    saving.value = false
  }
}

function startEdit(tag: Tag) {
  editId.value = tag.id
  editName.value = tag.name
}

function cancelEdit() {
  editId.value = ''
  editName.value = ''
}

async function saveEdit(tagId: string) {
  const name = editName.value.trim()
  if (!name) return
  saving.value = true
  try {
    const tag = await updateTag(tagId, name)
    cancelEdit()
    toast.success(`Updated to "${tag.name}".`)
    await loadTags()
  } catch (err) {
    toast.error(err instanceof Error ? err.message : String(err))
  } finally {
    saving.value = false
  }
}

async function handleDeleteTag(tag: Tag) {
  let usageNote = ''
  try {
    const { total } = await listEntries({ tag: tag.name, limit: 1 })
    usageNote =
      total > 0 ? ` It is currently used on ${total} entr${total === 1 ? 'y' : 'ies'}.` : ''
  } catch {
    // Usage count is a nice-to-have for the confirmation copy — if it fails
    // to load, fall back to the generic warning rather than blocking delete.
  }
  const ok = await confirm({
    title: `Delete "${tag.name}"?`,
    description: `This removes the tag from every entry it's applied to.${usageNote}`,
    confirmLabel: 'Delete tag',
    variant: 'destructive',
  })
  if (!ok) return
  saving.value = true
  try {
    await deleteTag(tag.id)
    toast.success(`Removed "${tag.name}".`)
    await loadTags()
  } catch (err) {
    toast.error(err instanceof Error ? err.message : String(err))
  } finally {
    saving.value = false
  }
}

function sortableHeader(label: string, column: { toggleSorting: (desc?: boolean) => void }) {
  return h(
    Button,
    {
      variant: 'ghost',
      size: 'sm',
      class: '-ml-3 h-8',
      onClick: () => column.toggleSorting(),
    },
    () => [label, h(ArrowUpDown, { class: 'ml-2 size-3.5' })]
  )
}

const columns: ColumnDef<Tag>[] = [
  {
    accessorKey: 'name',
    header: ({ column }) => sortableHeader('Name', column),
    cell: ({ row }) => {
      const tag = row.original
      if (editId.value === tag.id) {
        return h(Input, {
          class: 'h-8 w-48',
          type: 'text',
          modelValue: editName.value,
          'onUpdate:modelValue': (v: string | number) => (editName.value = String(v)),
        })
      }
      return h(Badge, { variant: 'secondary' }, () => tag.name)
    },
  },
  {
    id: 'actions',
    header: '',
    enableSorting: false,
    cell: ({ row }) => {
      const tag = row.original
      if (editId.value === tag.id) {
        return h('div', { class: 'flex gap-2' }, [
          h(
            Button,
            {
              type: 'button',
              size: 'sm',
              variant: 'outline',
              disabled: saving.value,
              onClick: () => saveEdit(tag.id),
            },
            () => 'Save'
          ),
          h(
            Button,
            { type: 'button', size: 'sm', variant: 'ghost', onClick: cancelEdit },
            () => 'Cancel'
          ),
        ])
      }
      return h('div', { class: 'flex gap-2' }, [
        h(
          Button,
          { type: 'button', size: 'sm', variant: 'ghost', onClick: () => startEdit(tag) },
          () => 'Edit'
        ),
        h(
          Button,
          { type: 'button', size: 'sm', variant: 'ghost', onClick: () => handleDeleteTag(tag) },
          () => 'Delete'
        ),
      ])
    },
  },
]

const sorting = ref<SortingState>([])

const table = useVueTable({
  get data() {
    return tags.value
  },
  columns,
  state: {
    get sorting() {
      return sorting.value
    },
  },
  onSortingChange: (updaterOrValue) => {
    sorting.value =
      typeof updaterOrValue === 'function' ? updaterOrValue(sorting.value) : updaterOrValue
  },
  getCoreRowModel: getCoreRowModel(),
  getSortedRowModel: getSortedRowModel(),
})

onMounted(loadTags)
</script>

<template>
  <div class="flex flex-col gap-6">
    <div>
      <h2 class="text-2xl font-semibold">Tag management</h2>
      <p class="mt-1 text-muted-foreground">
        Create, edit, or delete tags used across knowledge base entries.
      </p>
    </div>

    <Card>
      <CardContent class="grid gap-2 pt-6">
        <Label for="new-tag">New tag</Label>
        <div class="flex gap-2">
          <Input
            id="new-tag"
            v-model="newName"
            type="text"
            placeholder="e.g. onboarding, api, security"
            :disabled="saving"
            @keyup.enter="handleCreateTag"
          />
          <Button type="button" :disabled="saving || !newName.trim()" @click="handleCreateTag">
            {{ saving ? 'Saving…' : 'Create tag' }}
          </Button>
        </div>
      </CardContent>
    </Card>

    <Card>
      <CardContent class="pt-6">
        <p v-if="loading" class="text-sm text-muted-foreground">Loading tags…</p>
        <Alert v-else-if="loadError" variant="destructive" role="alert">
          <AlertCircle class="size-4" aria-hidden="true" />
          <AlertTitle>Couldn't load tags</AlertTitle>
          <AlertDescription>{{ loadError }}</AlertDescription>
        </Alert>
        <p v-else-if="!tags.length" class="text-sm text-muted-foreground">
          No tags in the catalog yet.
        </p>

        <Table v-else data-test="tags-list">
          <TableHeader>
            <TableRow v-for="headerGroup in table.getHeaderGroups()" :key="headerGroup.id">
              <TableHead
                v-for="header in headerGroup.headers"
                :key="header.id"
                :class="header.column.id === 'actions' ? 'w-40' : ''"
              >
                <FlexRender
                  v-if="!header.isPlaceholder"
                  :render="header.column.columnDef.header"
                  :props="header.getContext()"
                />
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow
              v-for="row in table.getRowModel().rows"
              :key="row.id"
              :data-test="`tag-row-${row.original.id}`"
            >
              <TableCell v-for="cell in row.getVisibleCells()" :key="cell.id">
                <FlexRender :render="cell.column.columnDef.cell" :props="cell.getContext()" />
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  </div>
</template>
