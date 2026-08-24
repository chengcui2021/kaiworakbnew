<script setup lang="ts">
import { computed, h, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  FlexRender,
  getCoreRowModel,
  getSortedRowModel,
  useVueTable,
  type ColumnDef,
  type SortingState,
} from '@tanstack/vue-table'
import { AlertCircle, ArrowUpDown, Search } from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import { useTemplateService } from '@/services/useTemplateService'
import { useConfirm } from '@/composables/useConfirm'
import type { Template } from '@/types/entry'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
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

const router = useRouter()
const { listTemplates, deleteTemplate } = useTemplateService()
const { confirm } = useConfirm()

const templates = ref<Template[]>([])
const loading = ref(false)
const deleting = ref(false)
const searchQuery = ref('')
const loadError = ref('')

const filteredTemplates = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return templates.value
  return templates.value.filter((t) => t.name.toLowerCase().includes(q))
})

async function loadTemplates() {
  loading.value = true
  loadError.value = ''
  try {
    const data = await listTemplates()
    templates.value = data.templates
  } catch (err) {
    loadError.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

async function handleDeleteTemplate(tpl: Template) {
  const ok = await confirm({
    title: `Delete "${tpl.name}"?`,
    description: 'This permanently removes the template.',
    confirmLabel: 'Delete template',
    variant: 'destructive',
  })
  if (!ok) return
  deleting.value = true
  try {
    await deleteTemplate(tpl.id)
    toast.success(`Removed "${tpl.name}".`)
    await loadTemplates()
  } catch (err) {
    toast.error(err instanceof Error ? err.message : String(err))
  } finally {
    deleting.value = false
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

const columns: ColumnDef<Template>[] = [
  {
    accessorKey: 'name',
    header: ({ column }) => sortableHeader('Name', column),
    cell: ({ row }) => {
      const tpl = row.original
      return h(
        'button',
        {
          type: 'button',
          class: 'cursor-pointer font-medium text-primary underline-offset-4 hover:underline',
          onClick: () => router.push({ name: 'edit-template', params: { id: tpl.id } }),
        },
        tpl.name
      )
    },
  },
  {
    id: 'actions',
    header: '',
    enableSorting: false,
    cell: ({ row }) => {
      const tpl = row.original
      return h('div', { class: 'flex gap-2' }, [
        h(
          Button,
          {
            type: 'button',
            size: 'sm',
            variant: 'ghost',
            onClick: () => router.push({ name: 'edit-template', params: { id: tpl.id } }),
          },
          () => 'Edit'
        ),
        h(
          Button,
          {
            type: 'button',
            size: 'sm',
            variant: 'ghost',
            onClick: () => handleDeleteTemplate(tpl),
          },
          () => 'Delete'
        ),
      ])
    },
  },
]

const sorting = ref<SortingState>([])

const table = useVueTable({
  get data() {
    return filteredTemplates.value
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

onMounted(loadTemplates)
</script>

<template>
  <div class="flex flex-col gap-6">
    <div>
      <h2 class="text-2xl font-semibold">Template management</h2>
      <p class="mt-1 text-muted-foreground">
        Create, edit, or delete document templates used for transforming entries.
      </p>
    </div>

    <div class="flex gap-2">
      <div class="relative flex-1">
        <Search class="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input v-model="searchQuery" type="text" placeholder="Search templates..." class="pl-9" />
      </div>
      <Button type="button" @click="router.push({ name: 'create-template' })">
        New Template
      </Button>
    </div>

    <Card>
      <CardContent class="pt-6">
        <p v-if="loading" class="text-sm text-muted-foreground">Loading templates…</p>
        <Alert v-else-if="loadError" variant="destructive" role="alert">
          <AlertCircle class="size-4" aria-hidden="true" />
          <AlertTitle>Couldn't load templates</AlertTitle>
          <AlertDescription>{{ loadError }}</AlertDescription>
        </Alert>
        <p v-else-if="!templates.length" class="text-sm text-muted-foreground">
          No templates yet. Click "New Template" to create one.
        </p>

        <Table v-else data-test="templates-list">
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
              :data-test="`template-row-${row.original.id}`"
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
