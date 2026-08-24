import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useGovernedContextService } from './useGovernedContextService'
import type { ContextAssemblyLock, GovernedContextRequest } from '@/types/governedContext'

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

const request: GovernedContextRequest = {
  request: { title: 'Add infusion guard', description: 'Guard the pump rate.' },
  repository: { name: 'metamorphic-kb', commit_sha: 'abc1234', branch: 'main' },
  knowledge: { entry_ids: ['11111111-1111-4111-8111-111111111111'] },
  governance: [{ id: 'gov-1', title: 'logging', topic: 'logging', rule: 'Log every dose change.' }],
}

const lock: ContextAssemblyLock = {
  lock_id: 'lock-abc',
  assembly_version: '1',
  context_hash: 'sha256:deadbeef',
  input_digests: { requirement_context: 'sha256:a' },
  governed_inputs: {
    request_id: null,
    request_digest: 'sha256:a',
    repository_commit_sha: 'abc1234',
    repository_digest: 'sha256:b',
    knowledge_entry_ids: ['11111111-1111-4111-8111-111111111111'],
    knowledge_hash: 'sha256:c',
    governance_rule_ids: ['gov-1'],
    governance_digest: 'sha256:d',
  },
  created_at: '2026-08-16T00:00:00Z',
}

describe('useGovernedContextService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('assembleGovernedContext POSTs the governed inputs to /api/governed-context/assemble', async () => {
    mockFetch.mockResolvedValueOnce(createFetchResponse({ context_hash: 'sha256:deadbeef' }))
    await useGovernedContextService().assembleGovernedContext(request)
    expect(mockFetch).toHaveBeenCalledWith(
      resolvedUrl('/api/governed-context/assemble'),
      expect.objectContaining({ method: 'POST', body: JSON.stringify(request) })
    )
  })

  it('createContextAssemblyLock POSTs to /api/governed-context/lock and returns the lock', async () => {
    mockFetch.mockResolvedValueOnce(createFetchResponse(lock))
    const result = await useGovernedContextService().createContextAssemblyLock(request)
    expect(mockFetch).toHaveBeenCalledWith(
      resolvedUrl('/api/governed-context/lock'),
      expect.objectContaining({ method: 'POST', body: JSON.stringify(request) })
    )
    // The lock must identify the governed inputs it was produced from.
    expect(result.governed_inputs.repository_commit_sha).toBe('abc1234')
    expect(result.context_hash).toBe('sha256:deadbeef')
  })

  it('checkContextAssemblyLock POSTs { lock, current } to /api/governed-context/lock/status', async () => {
    mockFetch.mockResolvedValueOnce(
      createFetchResponse({ lock_id: 'lock-abc', stale: false, reasons: [] })
    )
    await useGovernedContextService().checkContextAssemblyLock(lock, request)
    expect(mockFetch).toHaveBeenCalledWith(
      resolvedUrl('/api/governed-context/lock/status'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ lock, current: request }),
      })
    )
  })

  it('surfaces the backend detail message when the inputs are rejected', async () => {
    mockFetch.mockResolvedValueOnce(
      createFetchResponse(
        { detail: 'request.title must not be empty or whitespace-only' },
        false,
        422,
        'Unprocessable Entity'
      )
    )
    await expect(useGovernedContextService().createContextAssemblyLock(request)).rejects.toThrow(
      'request.title must not be empty or whitespace-only'
    )
  })

  it('reports a governance conflict rather than a generic failure on 409', async () => {
    // The 409 body is a structured object, so there is no string `detail` to
    // fall back on — the service's error map has to carry the meaning.
    mockFetch.mockResolvedValueOnce(
      createFetchResponse(
        { detail: { error: 'governance_conflict', conflicts: [] } },
        false,
        409,
        'Conflict'
      )
    )
    await expect(useGovernedContextService().assembleGovernedContext(request)).rejects.toThrow(
      /Conflicting engineering governance inputs/
    )
  })
})
