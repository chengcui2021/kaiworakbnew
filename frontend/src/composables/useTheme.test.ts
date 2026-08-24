import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@vueuse/core', () => ({
  useColorMode: vi.fn(() => ({ value: 'light' })),
}))

import { useTheme } from './useTheme'

describe('useTheme', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('returns the current theme', () => {
    const { currentTheme } = useTheme()
    expect(['default', 'violet', 'blue']).toContain(currentTheme.value)
  })

  it('sets theme and persists to localStorage', () => {
    const { setTheme, currentTheme } = useTheme()
    setTheme('blue')
    expect(currentTheme.value).toBe('blue')
    expect(localStorage.getItem('app-theme')).toBe('blue')
  })

  it('returns available themes', () => {
    const { getAvailableThemes } = useTheme()
    const themes = getAvailableThemes()
    expect(themes).toHaveLength(3)
    expect(themes.map((t) => t.name)).toContain('default')
    expect(themes.map((t) => t.name)).toContain('violet')
    expect(themes.map((t) => t.name)).toContain('blue')
  })

  it('exposes isDark computed', () => {
    const { isDark } = useTheme()
    expect(typeof isDark.value).toBe('boolean')
  })

  it('setColorMode updates the color mode without throwing', () => {
    const { setColorMode } = useTheme()
    expect(() => setColorMode('dark')).not.toThrow()
    expect(() => setColorMode('light')).not.toThrow()
  })
})
