<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import {
  BadgeCheck,
  BookOpen,
  Boxes,
  ChevronRight,
  FileText,
  FilePlus2,
  Library,
  PackageCheck,
  GitBranch,
  Search,
  Stethoscope,
  Tags,
} from 'lucide-vue-next'
import { useUsageService } from '@/services/useUsageService'
import type { UsageSummary } from '@/types/usage'
import type { SidebarProps } from '@/components/ui/sidebar'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from '@/components/ui/sidebar'

const props = withDefaults(defineProps<SidebarProps>(), {
  collapsible: 'icon',
})

const route = useRoute()

const coreOpen = ref(true)
const extraOpen = ref(true)

const navItems = [
  { title: 'Approved Knowledge', to: '/approved', icon: BadgeCheck },
  { title: 'Context Packages', to: '/packages', icon: PackageCheck },
  { title: 'Medical Device PoC', to: '/medical-device-poc', icon: Stethoscope },
]

const entryNavItems = [
  { title: 'Workspaces', to: '/workspaces', icon: Boxes },
  { title: 'Workstreams', to: '/workstreams', icon: Boxes },
  { title: 'Knowledge Sources', to: '/sources', icon: GitBranch },
  { title: 'Submit Entry', to: '/submit', icon: FilePlus2 },
  { title: 'Browse Entries', to: '/browse', icon: Library },
  { title: 'Search', to: '/search', icon: Search },
  { title: 'Tags', to: '/tags', icon: Tags },
  { title: 'Templates', to: '/templates', icon: FileText },
]

const { getUsageSummary } = useUsageService()
const usage = ref<UsageSummary | null>(null)

function isActive(to: string): boolean {
  if (route.path === to || route.path.startsWith(`${to}/`)) return true
  // /entries/:id/edit isn't nested under /browse in the URL, but it's the
  // detail view for an entry surfaced from Browse — keep that nav item lit
  // so editing an entry doesn't lose the sidebar's sense of "where am I."
  if (to === '/browse' && route.path.startsWith('/entries/')) return true
  return false
}

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`
  return String(n)
}

function formatCost(usd: number): string {
  if (usd < 0.01) return `$${usd.toFixed(4)}`
  return `$${usd.toFixed(2)}`
}

onMounted(async () => {
  try {
    usage.value = await getUsageSummary()
  } catch {
    // Silently ignore — footer just won't show usage stats
  }
})
</script>

<template>
  <Sidebar v-bind="props">
    <SidebarHeader>
      <SidebarMenu>
        <SidebarMenuItem>
          <SidebarMenuButton size="lg" as-child>
            <RouterLink to="/workspaces">
              <div
                class="flex aspect-square size-8 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground"
              >
                <BookOpen class="size-4" aria-hidden="true" />
              </div>
              <div class="flex flex-col gap-0.5 leading-none">
                <span class="font-semibold">Kaiwora KB</span>
                <span class="text-xs">Governed Engineering Knowledge</span>
              </div>
            </RouterLink>
          </SidebarMenuButton>
        </SidebarMenuItem>
      </SidebarMenu>
    </SidebarHeader>

    <SidebarContent>
      <SidebarGroup>
        <SidebarGroupLabel
          as="button"
          class="flex w-full cursor-pointer items-center"
          @click="coreOpen = !coreOpen"
        >
          CORE
          <ChevronRight
            class="ml-auto size-4 transition-transform"
            :class="coreOpen && 'rotate-90'"
          />
        </SidebarGroupLabel>
        <SidebarGroupContent v-show="coreOpen">
          <SidebarMenu>
            <SidebarMenuItem v-for="item in entryNavItems" :key="item.to">
              <SidebarMenuButton :is-active="isActive(item.to)" :tooltip="item.title" as-child>
                <RouterLink :to="item.to">
                  <component :is="item.icon" />
                  <span>{{ item.title }}</span>
                </RouterLink>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>

      <SidebarGroup>
        <SidebarGroupLabel
          as="button"
          class="flex w-full cursor-pointer items-center"
          @click="extraOpen = !extraOpen"
        >
          EXTRA
          <ChevronRight
            class="ml-auto size-4 transition-transform"
            :class="extraOpen && 'rotate-90'"
          />
        </SidebarGroupLabel>
        <SidebarGroupContent v-show="extraOpen">
          <SidebarMenu>
            <SidebarMenuItem v-for="item in navItems" :key="item.to">
              <SidebarMenuButton :is-active="isActive(item.to)" :tooltip="item.title" as-child>
                <RouterLink :to="item.to">
                  <component :is="item.icon" />
                  <span>{{ item.title }}</span>
                </RouterLink>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>
    </SidebarContent>

    <SidebarFooter v-if="usage" class="border-t border-sidebar-border">
      <div class="px-1 py-0.5 text-xs text-muted-foreground">
        <span>{{ formatTokens(usage.total_input_tokens + usage.total_output_tokens) }} tokens</span>
        <span class="mx-1">&middot;</span>
        <span>{{ formatCost(usage.estimated_cost_usd) }}</span>
        <span class="mx-1">&middot;</span>
        <span>{{ usage.total_calls }} {{ usage.total_calls === 1 ? 'call' : 'calls' }}</span>
      </div>
    </SidebarFooter>

    <SidebarRail />
  </Sidebar>
</template>
