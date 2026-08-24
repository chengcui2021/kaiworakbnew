<script setup lang="ts">
import { computed, ref } from 'vue'
import { Check, Moon, Sun, Palette, ChevronDown } from 'lucide-vue-next'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Button } from '@/components/ui/button'
import { useTheme } from '@/composables/useTheme'

const { currentTheme, colorMode, setTheme, setColorMode, getAvailableThemes, isDark } = useTheme()

const getModeIcon = () => {
  return isDark.value ? Moon : Sun
}

const themes = getAvailableThemes()

const currentThemeLabel = computed(() => {
  return themes.find((t) => t.name === currentTheme.value)?.label || 'Default'
})

const isThemeDropdownOpen = ref(false)
</script>

<template>
  <div class="flex items-center gap-2">
    <!-- Theme Dropdown -->
    <DropdownMenu v-model:open="isThemeDropdownOpen">
      <DropdownMenuTrigger as-child>
        <Button type="button" variant="ghost" size="sm" class="gap-2" aria-label="Theme">
          <Palette class="h-4 w-4" />
          <span class="hidden sm:inline">{{ currentThemeLabel }}</span>
          <ChevronDown class="h-4 w-4 opacity-50" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" class="w-56">
        <DropdownMenuItem
          v-for="theme in themes"
          :key="theme.name"
          @click="
            () => {
              setTheme(theme.name)
              isThemeDropdownOpen = false
            }
          "
        >
          <Palette class="w-4 h-4 mr-2" />
          <div class="flex flex-col">
            <span class="font-medium">{{ theme.label }}</span>
            <span class="text-xs text-muted-foreground">{{ theme.name }} theme variant</span>
          </div>
          <Check v-if="currentTheme === theme.name" class="ml-auto size-4" aria-hidden="true" />
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>

    <!-- Appearance Dropdown -->
    <DropdownMenu>
      <DropdownMenuTrigger as-child>
        <Button type="button" variant="ghost" size="sm" class="gap-2" aria-label="Appearance">
          <component :is="getModeIcon()" class="h-4 w-4" />
          <span class="hidden sm:inline">Appearance</span>
          <ChevronDown class="h-4 w-4 opacity-50" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" class="w-56">
        <DropdownMenuItem @click="setColorMode('light')">
          <Sun class="w-4 h-4 mr-2" />
          <div class="flex flex-col">
            <span class="font-medium">Light Mode</span>
            <span class="text-xs text-muted-foreground">Always use light theme</span>
          </div>
          <Check v-if="colorMode === 'light'" class="ml-auto size-4" aria-hidden="true" />
        </DropdownMenuItem>
        <DropdownMenuItem @click="setColorMode('dark')">
          <Moon class="w-4 h-4 mr-2" />
          <div class="flex flex-col">
            <span class="font-medium">Dark Mode</span>
            <span class="text-xs text-muted-foreground">Always use dark theme</span>
          </div>
          <Check v-if="colorMode === 'dark'" class="ml-auto size-4" aria-hidden="true" />
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  </div>
</template>
