import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useDocumentService } from './useDocumentService'

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

describe('useDocumentService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('listDocuments calls GET /api/workspaces/:id/documents with no query when unfiltered', async () => {
    mockFetch.mockResolvedValueOnce(createFetchResponse([]))
    await useDocumentService().listDocuments('ws-1')
    expect(mockFetch).toHaveBeenCalledWith(
      resolvedUrl('/api/workspaces/ws-1/documents'),
      expect.objectContaining({ method: 'GET' })
    )
  })

  it('listDocuments adds an approval_status query param when filtered', async () => {
    mockFetch.mockResolvedValueOnce(createFetchResponse([]))
    await useDocumentService().listDocuments('ws-1', 'approved')
    expect(mockFetch).toHaveBeenCalledWith(
      resolvedUrl('/api/workspaces/ws-1/documents?approval_status=approved'),
      expect.objectContaining({ method: 'GET' })
    )
  })

  it('createDocument calls POST /api/workspaces/:id/documents with title and content', async () => {
    mockFetch.mockResolvedValueOnce(createFetchResponse({}))
    await useDocumentService().createDocument('ws-1', { title: 'Doc', content: 'Body' })
    expect(mockFetch).toHaveBeenCalledWith(
      resolvedUrl('/api/workspaces/ws-1/documents'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ title: 'Doc', content: 'Body' }),
      })
    )
  })

  it('createDocument defaults content to empty string', async () => {
    mockFetch.mockResolvedValueOnce(createFetchResponse({}))
    await useDocumentService().createDocument('ws-1', { title: 'Doc' })
    expect(mockFetch).toHaveBeenCalledWith(
      resolvedUrl('/api/workspaces/ws-1/documents'),
      expect.objectContaining({
        body: JSON.stringify({ title: 'Doc', content: '' }),
      })
    )
  })

  it('deleteDocument calls DELETE /api/workspaces/:wsId/documents/:docId', async () => {
    mockFetch.mockResolvedValueOnce(createFetchResponse({ id: 'doc-1', deleted: true }))
    await useDocumentService().deleteDocument('ws-1', 'doc-1')
    expect(mockFetch).toHaveBeenCalledWith(
      resolvedUrl('/api/workspaces/ws-1/documents/doc-1'),
      expect.objectContaining({ method: 'DELETE' })
    )
  })

  it('moveDocument calls POST .../move with the target workspace id', async () => {
    mockFetch.mockResolvedValueOnce(createFetchResponse({}))
    await useDocumentService().moveDocument('ws-1', 'doc-1', 'ws-2')
    expect(mockFetch).toHaveBeenCalledWith(
      resolvedUrl('/api/workspaces/ws-1/documents/doc-1/move'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ target_workspace_id: 'ws-2' }),
      })
    )
  })

  it('setDocumentStatus calls PUT .../status with the approval status', async () => {
    mockFetch.mockResolvedValueOnce(createFetchResponse({}))
    await useDocumentService().setDocumentStatus('ws-1', 'doc-1', 'approved')
    expect(mockFetch).toHaveBeenCalledWith(
      resolvedUrl('/api/workspaces/ws-1/documents/doc-1/status'),
      expect.objectContaining({
        method: 'PUT',
        body: JSON.stringify({ approval_status: 'approved' }),
      })
    )
  })
})
