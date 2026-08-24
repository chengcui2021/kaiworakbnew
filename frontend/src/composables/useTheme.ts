/**
 * Theme Management Composable
 *
 * Manages theme switching using CSS classes on the HTML element.
 * Supports both color mode (light/dark) and theme variants (default, violet, blue).
 * All theme CSS files are imported statically, and we toggle classes to switch themes.
 *
 * This composable uses a singleton pattern - all components share the same theme state.
 */

import { ref, computed } from 'vue'
import { useColorMode } from '@vueuse/core'

export type ThemeName = 'default' | 'violet' | 'blue'
export type ColorMode = 'light' | 'dark'

// Singleton state - shared across all component instances
const currentTheme = ref<ThemeName>('violet')
let initialized = false

// Use VueUse color mode for dark/light switching
const colorMode = useColorMode({
  selector: 'html',
  attribute: 'class',
  modes: {
    light: '',
    dark: 'dark',
  },
  storageKey: 'vueuse-color-scheme',
})

/**
 * Apply theme class to HTML element
 */
function applyTheme(theme: ThemeName) {
  const html = document.documentElement

  // Remove all theme classes
  html.classList.remove('theme-default', 'theme-violet', 'theme-blue')

  // Add current theme class
  html.classList.add(`theme-${theme}`)
}

/**
 * Initialize theme from localStorage
 */
function initializeTheme() {
  if (initialized) return

  // Load saved theme from localStorage or use default
  const savedTheme = (localStorage.getItem('app-theme') as ThemeName) || 'violet'
  currentTheme.value = savedTheme
  applyTheme(savedTheme)
  initialized = true
}

/**
 * Set the current theme
 */
function setTheme(theme: ThemeName) {
  currentTheme.value = theme
  applyTheme(theme)

  // Save to localStorage
  localStorage.setItem('app-theme', theme)
}

/**
 * Set the color mode (light/dark)
 */
function setColorMode(mode: ColorMode) {
  colorMode.value = mode
}

/**
 * Get available themes
 */
function getAvailableThemes(): Array<{ name: ThemeName; label: string }> {
  return [
    { name: 'default', label: 'Default' },
    { name: 'violet', label: 'Violet' },
    { name: 'blue', label: 'Blue' },
  ]
}

// Initialize on first use
initializeTheme()

export function useTheme() {
  // Ensure theme is initialized when composable is used
  if (!initialized) {
    initializeTheme()
  }

  return {
    currentTheme: computed(() => currentTheme.value),
    colorMode: computed(() => colorMode.value as ColorMode),
    setTheme,
    setColorMode,
    getAvailableThemes,
    isDark: computed(() => colorMode.value === 'dark'),
  }
}
