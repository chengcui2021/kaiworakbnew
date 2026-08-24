<script setup lang="ts">
import { ChevronDown, FolderOpen } from 'lucide-vue-next'
import { useWorkspace } from '../composables/useWorkspace'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'

const { activeWorkspace, workspaces, setActiveWorkspace } = useWorkspace()
</script>

<template>
  <DropdownMenu>
    <DropdownMenuTrigger as-child>
      <Button
        variant="outline"
        size="sm"
        class="gap-2"
        data-test="workspace-indicator-trigger"
        :aria-label="
          activeWorkspace ? `Active workspace: ${activeWorkspace.name}` : 'No workspace selected'
        "
      >
        <FolderOpen class="size-4" />
        <Tooltip v-if="activeWorkspace">
          <TooltipTrigger as-child>
            <span class="hidden sm:inline" data-test="active-workspace-name">{{
              activeWorkspace.name
            }}</span>
          </TooltipTrigger>
          <TooltipContent>Workspace ID: {{ activeWorkspace.id }}</TooltipContent>
        </Tooltip>
        <Badge v-else variant="destructive">No Workspace Selected</Badge>
        <ChevronDown class="size-4 opacity-50" />
      </Button>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="end" class="w-64">
      <DropdownMenuItem
        v-for="ws in workspaces"
        :key="ws.id"
        :data-test="`workspace-option-${ws.id}`"
        @click="setActiveWorkspace(ws.id)"
      >
        <span class="flex-1">{{ ws.name }}</span>
        <Badge v-if="ws.id === activeWorkspace?.id" variant="secondary">Active</Badge>
      </DropdownMenuItem>
      <DropdownMenuItem v-if="!workspaces.length" disabled>No workspaces yet</DropdownMenuItem>
    </DropdownMenuContent>
  </DropdownMenu>
</template>
