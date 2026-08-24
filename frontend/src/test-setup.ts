import { vi } from 'vitest'

// Silence console output during tests to keep output clean.
// Error paths are tested via assertions, not console output.
vi.spyOn(console, 'log').mockImplementation(() => {})
vi.spyOn(console, 'warn').mockImplementation(() => {})
vi.spyOn(console, 'error').mockImplementation(() => {})
