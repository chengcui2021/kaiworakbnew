<script setup lang="ts">
import { h, ref } from 'vue'
import {
  FlexRender,
  getCoreRowModel,
  getSortedRowModel,
  useVueTable,
  type ColumnDef,
  type SortingState,
} from '@tanstack/vue-table'
import { ArrowUpDown, MoreHorizontal } from 'lucide-vue-next'
import { formatDate } from '../utils/format'
import type { ApprovalStatus, KbDocument, Workspace } from '../types/domain'
import ApprovalBadge from './ApprovalBadge.vue'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

const props = defineProps<{
  documents: KbDocument[]
  emptyText?: string
  // When true, show per-document delete / move controls.
  actions?: boolean
  // When true, show approval status controls (approve / archive / draft).
  approval?: boolean
  // Candidate destination workspaces for the "move" control (excludes current).
  moveTargets?: Workspace[]
}>()

const emit = defineEmits<{
  (e: 'delete', doc: KbDocument): void
  (e: 'move', payload: { doc: KbDocument; targetWorkspaceId: string }): void
  (e: 'status-change', payload: { doc: KbDocument; status: ApprovalStatus }): void
}>()

const STATUS_LABEL: Record<ApprovalStatus, string> = {
  draft: 'Draft',
  approved: 'Approve',
  archived: 'Archive',
}

function changeStatus(doc: KbDocument, status: ApprovalStatus) {
  if (doc.approval_status === status) return
  emit('status-change', { doc, status })
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

const columns: ColumnDef<KbDocument>[] = [
  {
    accessorKey: 'title',
    header: ({ column }) => sortableHeader('Title', column),
    cell: ({ row }) => {
      const doc = row.original
      return h('div', {}, [
        h('div', { class: 'font-medium' }, doc.title),
        h('p', { class: 'line-clamp-1 text-sm text-muted-foreground' }, doc.content),
        h(
          'span',
          { class: 'text-xs text-muted-foreground', 'data-test': `doc-ws-${doc.id}` },
          doc.workspace_id
        ),
      ])
    },
  },
  {
    accessorKey: 'approval_status',
    header: ({ column }) => sortableHeader('Status', column),
    cell: ({ row }) => h(ApprovalBadge, { status: row.original.approval_status }),
  },
  {
    accessorKey: 'updated_at',
    header: ({ column }) => sortableHeader('Updated', column),
    cell: ({ row }) => {
      const doc = row.original
      const children: (string | ReturnType<typeof h>)[] = [formatDate(doc.updated_at)]
      if (doc.approved_at) {
        children.push(h('br'), `Approved ${formatDate(doc.approved_at)}`)
      }
      return h('span', { class: 'text-sm text-muted-foreground' }, children)
    },
  },
  {
    id: 'actions',
    header: '',
    enableSorting: false,
    cell: ({ row }) => {
      if (!props.approval && !props.actions) return null
      const doc = row.original
      return h(DropdownMenu, {}, () => [
        h(DropdownMenuTrigger, { asChild: true }, () =>
          h(
            Button,
            { variant: 'ghost', size: 'icon-sm', 'data-test': `doc-actions-${doc.id}` },
            () => h(MoreHorizontal, { class: 'size-4' })
          )
        ),
        h(DropdownMenuContent, { align: 'end' }, () => {
          const items = []
          if (props.approval) {
            items.push(h(DropdownMenuLabel, {}, () => 'Set status'))
            for (const status of ['draft', 'approved', 'archived'] as const) {
              items.push(
                h(
                  DropdownMenuItem,
                  {
                    key: status,
                    disabled: doc.approval_status === status,
                    'data-test': `doc-set-${status}-${doc.id}`,
                    onClick: () => changeStatus(doc, status),
                  },
                  () => STATUS_LABEL[status]
                )
              )
            }
          }
          if (props.actions) {
            if (props.approval) items.push(h(DropdownMenuSeparator))
            if (props.moveTargets?.length) {
              items.push(
                h(DropdownMenuSub, {}, () => [
                  h(
                    DropdownMenuSubTrigger,
                    { 'data-test': `doc-move-${doc.id}` },
                    () => 'Move to…'
                  ),
                  h(DropdownMenuSubContent, {}, () =>
                    (props.moveTargets ?? []).map((ws) =>
                      h(
                        DropdownMenuItem,
                        {
                          key: ws.id,
                          onClick: () => emit('move', { doc, targetWorkspaceId: ws.id }),
                        },
                        () => ws.name
                      )
                    )
                  ),
                ])
              )
            }
            items.push(
              h(
                DropdownMenuItem,
                {
                  variant: 'destructive',
                  'data-test': `doc-delete-${doc.id}`,
                  onClick: () => emit('delete', doc),
                },
                () => 'Delete'
              )
            )
          }
          return items
        }),
      ])
    },
  },
]

const sorting = ref<SortingState>([])

const table = useVueTable({
  get data() {
    return props.documents
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
</script>

<template>
  <Table v-if="documents.length" data-test="document-list">
    <TableHeader>
      <TableRow v-for="headerGroup in table.getHeaderGroups()" :key="headerGroup.id">
        <TableHead
          v-for="header in headerGroup.headers"
          :key="header.id"
          :class="header.column.id === 'actions' ? 'w-10' : ''"
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
      <TableRow v-for="row in table.getRowModel().rows" :key="row.id">
        <TableCell v-for="cell in row.getVisibleCells()" :key="cell.id">
          <FlexRender :render="cell.column.columnDef.cell" :props="cell.getContext()" />
        </TableCell>
      </TableRow>
    </TableBody>
  </Table>
  <p v-else class="text-sm text-muted-foreground">{{ emptyText || 'No documents yet.' }}</p>
</template>
