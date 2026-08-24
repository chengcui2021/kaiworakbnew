<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import type { BreadcrumbItem } from '@/types/router'
import { useWorkspace } from '@/composables/useWorkspace'
import AppSidebar from '@/components/AppSidebar.vue'
import WorkspaceIndicator from '@/components/WorkspaceIndicator.vue'
import WorkstreamIndicator from '@/components/WorkstreamIndicator.vue'
import ThemeSwitcher from '@/components/ThemeSwitcher.vue'
import { SidebarProvider, SidebarInset, SidebarTrigger } from '@/components/ui/sidebar'
import {
  Breadcrumb,
  BreadcrumbList,
  BreadcrumbItem as BreadcrumbItemComponent,
  BreadcrumbLink,
  BreadcrumbSeparator,
  BreadcrumbPage,
} from '@/components/ui/breadcrumb'
import { Separator } from '@/components/ui/separator'

const route = useRoute()
const { workspaces } = useWorkspace()

const breadcrumbs = computed<BreadcrumbItem[]>(() => {
  const base = route.meta.breadcrumb || []
  if (route.name === 'workspace-detail') {
    const ws = workspaces.value.find((w) => w.id === route.params.id)
    return [...base, { label: ws?.name || String(route.params.id), to: null }]
  }
  return base
})
</script>

<template>
  <SidebarProvider>
    <AppSidebar />
    <SidebarInset>
      <header class="flex h-16 shrink-0 items-center gap-2 border-b px-4">
        <SidebarTrigger class="-ml-1" />
        <Separator orientation="vertical" class="mr-2 h-4" />
        <Breadcrumb v-if="breadcrumbs.length > 0">
          <BreadcrumbList>
            <template v-for="(crumb, index) in breadcrumbs" :key="index">
              <BreadcrumbItemComponent>
                <BreadcrumbLink v-if="crumb.to && index < breadcrumbs.length - 1" as-child>
                  <RouterLink :to="crumb.to">{{ crumb.label }}</RouterLink>
                </BreadcrumbLink>
                <BreadcrumbPage v-else>{{ crumb.label }}</BreadcrumbPage>
              </BreadcrumbItemComponent>
              <BreadcrumbSeparator v-if="index < breadcrumbs.length - 1" />
            </template>
          </BreadcrumbList>
        </Breadcrumb>
        <div class="ml-auto flex items-center gap-2">
          <WorkspaceIndicator />
          <WorkstreamIndicator />
          <ThemeSwitcher />
        </div>
      </header>
      <main class="flex-1 p-6">
        <slot />
      </main>
    </SidebarInset>
  </SidebarProvider>
</template>
