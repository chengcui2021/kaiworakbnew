<script setup lang="ts">
import { ChevronDown, FolderOpen } from 'lucide-vue-next'
import { useWorkstream } from '../composables/useWorkstream'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'

const { activeWorkstream, workstreams, setActiveWorkstream } = useWorkstream()
</script>

<template>
  <DropdownMenu>
    <DropdownMenuTrigger as-child>
      <Button
        variant="outline"
        size="sm"
        class="gap-2"
        data-test="workstream-indicator-trigger"
        :aria-label="
          activeWorkstream
            ? `Active workstream: ${activeWorkstream.name}`
            : 'No workstream selected'
        "
      >
        <FolderOpen class="size-4" />
        <Tooltip v-if="activeWorkstream">
          <TooltipTrigger as-child>
            <span class="hidden sm:inline" data-test="active-workstream-name">{{
              activeWorkstream.name
            }}</span>
          </TooltipTrigger>
          <TooltipContent>Workstream ID: {{ activeWorkstream.id }}</TooltipContent>
        </Tooltip>
        <Badge v-else variant="destructive">No Workstream Selected</Badge>
        <ChevronDown class="size-4 opacity-50" />
      </Button>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="end" class="w-64">
      <DropdownMenuItem
        v-for="ws in workstreams"
        :key="ws.id"
        :data-test="`workstream-option-${ws.id}`"
        @click="setActiveWorkstream(ws.id)"
      >
        <span class="flex-1">{{ ws.name }}</span>
        <Badge v-if="ws.id === activeWorkstream?.id" variant="secondary">Active</Badge>
      </DropdownMenuItem>
      <DropdownMenuItem v-if="!workstreams.length" disabled>No workstreams yet</DropdownMenuItem>
    </DropdownMenuContent>
  </DropdownMenu>
</template>
