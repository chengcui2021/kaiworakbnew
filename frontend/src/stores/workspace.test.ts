import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useWorkspaceStore } from './workspace'
import type { Workspace } from '@/types/domain'

const ACTIVE_WORKSPACE_KEY = 'kb.activeWorkspaceId'

const mockWorkspaceService = {
  listWorkspaces: vi.fn(),
}

vi.mock('@/services/useWorkspaceService', () => ({
  useWorkspaceService: () => mockWorkspaceService,
}))

function makeWorkspace(overrides: Partial<Workspace> = {}): Workspace {
  return {
    id: 'ws-1',
    name: 'Test Workspace',
    description: '',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    document_count: 0,
    ...overrides,
  }
}

describe('workspace store', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    setActivePinia(createPinia())
  })

  describe('initial state', () => {
    it('starts empty with no active workspace when localStorage is empty', () => {
      const store = useWorkspaceStore()
      expect(store.workspaces).toEqual([])
      expect(store.activeWorkspaceId).toBeNull()
      expect(store.activeWorkspace).toBeNull()
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })

    it('reads the persisted active workspace id from localStorage on init', () => {
      localStorage.setItem(ACTIVE_WORKSPACE_KEY, 'ws-persisted')
      const store = useWorkspaceStore()
      expect(store.activeWorkspaceId).toBe('ws-persisted')
    })
  })

  describe('loadWorkspaces', () => {
    it('populates workspaces from the service', async () => {
      const workspaces = [makeWorkspace({ id: 'ws-1' }), makeWorkspace({ id: 'ws-2' })]
      mockWorkspaceService.listWorkspaces.mockResolvedValue(workspaces)

      const store = useWorkspaceStore()
      await store.loadWorkspaces()

      expect(store.workspaces).toEqual(workspaces)
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })

    it('auto-selects the first workspace when there is no valid active selection', async () => {
      const workspaces = [makeWorkspace({ id: 'ws-1' }), makeWorkspace({ id: 'ws-2' })]
      mockWorkspaceService.listWorkspaces.mockResolvedValue(workspaces)

      const store = useWorkspaceStore()
      await store.loadWorkspaces()

      expect(store.activeWorkspaceId).toBe('ws-1')
      expect(localStorage.getItem(ACTIVE_WORKSPACE_KEY)).toBe('ws-1')
    })

    it('preserves a still-valid persisted active selection', async () => {
      localStorage.setItem(ACTIVE_WORKSPACE_KEY, 'ws-2')
      const workspaces = [makeWorkspace({ id: 'ws-1' }), makeWorkspace({ id: 'ws-2' })]
      mockWorkspaceService.listWorkspaces.mockResolvedValue(workspaces)

      const store = useWorkspaceStore()
      await store.loadWorkspaces()

      expect(store.activeWorkspaceId).toBe('ws-2')
    })

    it('repairs the active selection when the persisted id no longer exists', async () => {
      localStorage.setItem(ACTIVE_WORKSPACE_KEY, 'ws-deleted')
      const workspaces = [makeWorkspace({ id: 'ws-1' })]
      mockWorkspaceService.listWorkspaces.mockResolvedValue(workspaces)

      const store = useWorkspaceStore()
      await store.loadWorkspaces()

      expect(store.activeWorkspaceId).toBe('ws-1')
    })

    it('clears the active selection when no workspaces exist', async () => {
      mockWorkspaceService.listWorkspaces.mockResolvedValue([])

      const store = useWorkspaceStore()
      await store.loadWorkspaces()

      expect(store.activeWorkspaceId).toBeNull()
      expect(localStorage.getItem(ACTIVE_WORKSPACE_KEY)).toBeNull()
    })

    it('sets error state when the service call fails', async () => {
      mockWorkspaceService.listWorkspaces.mockRejectedValue(new Error('Network error'))

      const store = useWorkspaceStore()
      await store.loadWorkspaces()

      expect(store.error).toBe('Network error')
      expect(store.loading).toBe(false)
    })

    it('sets loading true during the request and false after', async () => {
      let resolvePromise: (value: Workspace[]) => void
      mockWorkspaceService.listWorkspaces.mockReturnValue(
        new Promise((resolve) => {
          resolvePromise = resolve
        })
      )

      const store = useWorkspaceStore()
      const promise = store.loadWorkspaces()
      expect(store.loading).toBe(true)

      resolvePromise!([])
      await promise
      expect(store.loading).toBe(false)
    })
  })

  describe('setActiveWorkspace', () => {
    it('persists the active workspace id to localStorage', () => {
      const store = useWorkspaceStore()
      store.setActiveWorkspace('ws-5')

      expect(store.activeWorkspaceId).toBe('ws-5')
      expect(localStorage.getItem(ACTIVE_WORKSPACE_KEY)).toBe('ws-5')
    })

    it('removes the key from localStorage when set to null', () => {
      localStorage.setItem(ACTIVE_WORKSPACE_KEY, 'ws-5')
      const store = useWorkspaceStore()
      store.setActiveWorkspace(null)

      expect(store.activeWorkspaceId).toBeNull()
      expect(localStorage.getItem(ACTIVE_WORKSPACE_KEY)).toBeNull()
    })
  })

  describe('activeWorkspace computed', () => {
    it('derives the full workspace object from activeWorkspaceId', async () => {
      const workspaces = [
        makeWorkspace({ id: 'ws-1', name: 'Alpha' }),
        makeWorkspace({ id: 'ws-2', name: 'Beta' }),
      ]
      mockWorkspaceService.listWorkspaces.mockResolvedValue(workspaces)

      const store = useWorkspaceStore()
      await store.loadWorkspaces()
      store.setActiveWorkspace('ws-2')

      expect(store.activeWorkspace).toEqual(workspaces[1])
    })

    it('is null when activeWorkspaceId does not match any workspace', async () => {
      mockWorkspaceService.listWorkspaces.mockResolvedValue([makeWorkspace({ id: 'ws-1' })])

      const store = useWorkspaceStore()
      await store.loadWorkspaces()
      store.setActiveWorkspace('ws-unknown')

      expect(store.activeWorkspace).toBeNull()
    })
  })
})
