import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useWorkspaceService } from './useWorkspaceService'

const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

function createFetchResponse(data: unknown, ok = true, status = 200, statusText = 'OK') {
  return {
    ok,
    status,
    statusText,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  }
}

function resolvedUrl(path: string) {
  const base = import.meta.env.VITE_API_BASE_URL || ''
  return `${base}${path}`
}

describe('useWorkspaceService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('listWorkspaces calls GET /api/workspaces', async () => {
    mockFetch.mockResolvedValueOnce(createFetchResponse([]))
    await useWorkspaceService().listWorkspaces()
    expect(mockFetch).toHaveBeenCalledWith(
      resolvedUrl('/api/workspaces'),
      expect.objectContaining({ method: 'GET' })
    )
  })

  it('getWorkspace calls GET /api/workspaces/:id', async () => {
    mockFetch.mockResolvedValueOnce(createFetchResponse({}))
    await useWorkspaceService().getWorkspace('ws-1')
    expect(mockFetch).toHaveBeenCalledWith(
      resolvedUrl('/api/workspaces/ws-1'),
      expect.objectContaining({ method: 'GET' })
    )
  })

  it('createWorkspace calls POST /api/workspaces with name and description', async () => {
    mockFetch.mockResolvedValueOnce(createFetchResponse({}))
    await useWorkspaceService().createWorkspace({ name: 'Foo', description: 'Bar' })
    expect(mockFetch).toHaveBeenCalledWith(
      resolvedUrl('/api/workspaces'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ name: 'Foo', description: 'Bar' }),
      })
    )
  })

  it('createWorkspace defaults description to empty string', async () => {
    mockFetch.mockResolvedValueOnce(createFetchResponse({}))
    await useWorkspaceService().createWorkspace({ name: 'Foo' })
    expect(mockFetch).toHaveBeenCalledWith(
      resolvedUrl('/api/workspaces'),
      expect.objectContaining({
        body: JSON.stringify({ name: 'Foo', description: '' }),
      })
    )
  })

  it('updateWorkspace calls PUT /api/workspaces/:id', async () => {
    mockFetch.mockResolvedValueOnce(createFetchResponse({}))
    await useWorkspaceService().updateWorkspace('ws-1', { name: 'Renamed' })
    expect(mockFetch).toHaveBeenCalledWith(
      resolvedUrl('/api/workspaces/ws-1'),
      expect.objectContaining({
        method: 'PUT',
        body: JSON.stringify({ name: 'Renamed' }),
      })
    )
  })

  it('deleteWorkspace calls DELETE /api/workspaces/:id', async () => {
    mockFetch.mockResolvedValueOnce(createFetchResponse({ id: 'ws-1', deleted: true }))
    await useWorkspaceService().deleteWorkspace('ws-1')
    expect(mockFetch).toHaveBeenCalledWith(
      resolvedUrl('/api/workspaces/ws-1'),
      expect.objectContaining({ method: 'DELETE' })
    )
  })

  it('getWorkspaceStats calls GET /api/workspaces/:id/stats', async () => {
    mockFetch.mockResolvedValueOnce(createFetchResponse({}))
    await useWorkspaceService().getWorkspaceStats('ws-1')
    expect(mockFetch).toHaveBeenCalledWith(
      resolvedUrl('/api/workspaces/ws-1/stats'),
      expect.objectContaining({ method: 'GET' })
    )
  })

  it('validateWorkspace calls GET /api/workspaces/:id/validate', async () => {
    mockFetch.mockResolvedValueOnce(createFetchResponse({}))
    await useWorkspaceService().validateWorkspace('ws-1')
    expect(mockFetch).toHaveBeenCalledWith(
      resolvedUrl('/api/workspaces/ws-1/validate'),
      expect.objectContaining({ method: 'GET' })
    )
  })

  it('listActivities calls GET /api/workspaces/:id/activities with a limit query param', async () => {
    mockFetch.mockResolvedValueOnce(createFetchResponse([]))
    await useWorkspaceService().listActivities('ws-1', 10)
    expect(mockFetch).toHaveBeenCalledWith(
      resolvedUrl('/api/workspaces/ws-1/activities?limit=10'),
      expect.objectContaining({ method: 'GET' })
    )
  })

  it('listActivities defaults the limit to 20', async () => {
    mockFetch.mockResolvedValueOnce(createFetchResponse([]))
    await useWorkspaceService().listActivities('ws-1')
    expect(mockFetch).toHaveBeenCalledWith(
      resolvedUrl('/api/workspaces/ws-1/activities?limit=20'),
      expect.objectContaining({ method: 'GET' })
    )
  })
})
