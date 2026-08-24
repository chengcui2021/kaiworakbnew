import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useTemplateService } from './useTemplateService'

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

describe('useTemplateService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('listTemplates calls GET /api/templates', async () => {
    mockFetch.mockResolvedValueOnce(createFetchResponse({ templates: [], count: 0 }))
    await useTemplateService().listTemplates()
    expect(mockFetch).toHaveBeenCalledWith(
      resolvedUrl('/api/templates'),
      expect.objectContaining({ method: 'GET' })
    )
  })

  it('getTemplate calls GET /api/templates/:id', async () => {
    mockFetch.mockResolvedValueOnce(createFetchResponse({ id: 't-1', name: 'Test' }))
    await useTemplateService().getTemplate('t-1')
    expect(mockFetch).toHaveBeenCalledWith(
      resolvedUrl('/api/templates/t-1'),
      expect.objectContaining({ method: 'GET' })
    )
  })

  it('createTemplate calls POST /api/templates with name and content', async () => {
    mockFetch.mockResolvedValueOnce(createFetchResponse({ id: 't-1', name: 'Spec' }))
    await useTemplateService().createTemplate({ name: 'Spec', content: '# Spec' })
    expect(mockFetch).toHaveBeenCalledWith(
      resolvedUrl('/api/templates'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ name: 'Spec', content: '# Spec' }),
      })
    )
  })

  it('updateTemplate calls PUT /api/templates/:id with name and content', async () => {
    mockFetch.mockResolvedValueOnce(createFetchResponse({ id: 't-1', name: 'Updated' }))
    await useTemplateService().updateTemplate('t-1', { name: 'Updated', content: '# Updated' })
    expect(mockFetch).toHaveBeenCalledWith(
      resolvedUrl('/api/templates/t-1'),
      expect.objectContaining({
        method: 'PUT',
        body: JSON.stringify({ name: 'Updated', content: '# Updated' }),
      })
    )
  })

  it('deleteTemplate calls DELETE /api/templates/:id', async () => {
    mockFetch.mockResolvedValueOnce(createFetchResponse(null, true, 204))
    await useTemplateService().deleteTemplate('t-1')
    expect(mockFetch).toHaveBeenCalledWith(
      resolvedUrl('/api/templates/t-1'),
      expect.objectContaining({ method: 'DELETE' })
    )
  })

  it('createTemplate rejects on 409 conflict', async () => {
    mockFetch.mockResolvedValueOnce(
      createFetchResponse({ detail: 'Template already exists' }, false, 409, 'Conflict')
    )
    await expect(
      useTemplateService().createTemplate({ name: 'Dup', content: '' })
    ).rejects.toThrow()
  })
})
