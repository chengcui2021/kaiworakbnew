import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  buildGovernedContextRequest,
  emptyGovernedContextInputs,
  parseGovernanceRules,
  partitionKnowledgeIds,
  useContextAssemblyLock,
  validateGovernedContextInputs,
} from './useContextAssemblyLock'
import type { ContextPackage } from '@/types/domain'
import type { GovernedContextInputs } from './useContextAssemblyLock'

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

const ENTRY_A = '11111111-1111-4111-8111-111111111111'
const ENTRY_B = '22222222-2222-4222-8222-222222222222'

function makePackage(overrides: Partial<ContextPackage> = {}): ContextPackage {
  return {
    id: 'pkg-persistent-1',
    name: 'Launch context',
    workspace_id: 'ws-1',
    selected_entry_ids: [ENTRY_A, ENTRY_B],
    created_at: '2026-08-16T00:00:00Z',
    approval_status: 'approved',
    context_hash: 'sha256:packagehash',
    entry_titles: ['Pump spec', 'Retrieval notes'],
    ...overrides,
  }
}

function makeInputs(overrides: Partial<GovernedContextInputs> = {}): GovernedContextInputs {
  return {
    ...emptyGovernedContextInputs(),
    requestTitle: 'Add infusion guard',
    requestDescription: 'Guard the pump rate against out-of-range doses.',
    repositoryName: 'metamorphic-kb',
    repositoryBranch: 'main',
    repositoryCommitSha: 'abc1234',
    ...overrides,
  }
}

const lockResponse = {
  lock_id: 'lock-deadbeef',
  assembly_version: '1',
  context_hash: 'sha256:deadbeef',
  input_digests: { requirement_context: 'sha256:a' },
  governed_inputs: {
    request_id: null,
    request_digest: 'sha256:a',
    repository_commit_sha: 'abc1234',
    repository_digest: 'sha256:b',
    knowledge_entry_ids: [ENTRY_A, ENTRY_B],
    knowledge_hash: 'sha256:c',
    governance_rule_ids: ['gov-1'],
    governance_digest: 'sha256:d',
  },
  created_at: '2026-08-16T00:00:00Z',
}

describe('governed context input helpers', () => {
  it('partitions persistent KB entry ids from workspace document ids', () => {
    expect(partitionKnowledgeIds([ENTRY_A, 'doc-1'])).toEqual({
      entryIds: [ENTRY_A],
      ineligibleIds: ['doc-1'],
    })
  })

  it('parses "topic :: rule" lines into approved governance rules', () => {
    expect(parseGovernanceRules('logging :: Log every dose change.\n\n  ')).toEqual([
      {
        id: 'gov-1',
        title: 'logging',
        topic: 'logging',
        rule: 'Log every dose change.',
        status: 'approved',
        precedence: 0,
      },
    ])
  })

  it('treats a line without a separator as its own topic and statement', () => {
    const [rule] = parseGovernanceRules('No unlogged dose changes')
    expect(rule.topic).toBe('No unlogged dose changes')
    expect(rule.rule).toBe('No unlogged dose changes')
  })

  it('rejects missing request/repository inputs and malformed commit SHAs', () => {
    expect(validateGovernedContextInputs(emptyGovernedContextInputs())).toHaveLength(4)
    expect(validateGovernedContextInputs(makeInputs({ repositoryCommitSha: 'nothex' }))).toEqual([
      'The repository commit SHA must be 7-64 hexadecimal characters.',
    ])
    expect(validateGovernedContextInputs(makeInputs())).toEqual([])
  })

  it('builds a request whose knowledge is the package selection and whose source is the package lineage', () => {
    const payload = buildGovernedContextRequest(makePackage(), makeInputs())
    expect(payload.knowledge.entry_ids).toEqual([ENTRY_A, ENTRY_B])
    expect(payload.repository).toEqual({
      name: 'metamorphic-kb',
      branch: 'main',
      commit_sha: 'abc1234',
    })
    expect(payload.request.source).toBe('metamorphic-kb:workspace/ws-1/package/pkg-persistent-1')
  })
})

describe('useContextAssemblyLock', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.stubGlobal('URL', {
      ...URL,
      createObjectURL: vi.fn(() => 'blob:lock'),
      revokeObjectURL: vi.fn(),
    })
  })

  it('locks through the backend and exposes the returned governed lock', async () => {
    mockFetch.mockResolvedValueOnce(createFetchResponse(lockResponse))
    const { exportContextLock, lock, errors } = useContextAssemblyLock()

    const result = await exportContextLock(makePackage(), makeInputs())

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/governed-context/lock'),
      expect.objectContaining({ method: 'POST' })
    )
    expect(result?.context_hash).toBe('sha256:deadbeef')
    expect(lock.value?.governed_inputs.knowledge_entry_ids).toEqual([ENTRY_A, ENTRY_B])
    expect(errors.value).toEqual([])
  })

  it('does not call the backend when the governed inputs are incomplete', async () => {
    const { exportContextLock, errors } = useContextAssemblyLock()

    const result = await exportContextLock(makePackage(), emptyGovernedContextInputs())

    expect(result).toBeNull()
    expect(mockFetch).not.toHaveBeenCalled()
    expect(errors.value.length).toBeGreaterThan(0)
  })

  it('refuses to lock a package holding entries that are not persistent KB knowledge', async () => {
    const { exportContextLock, errors } = useContextAssemblyLock()

    const result = await exportContextLock(
      makePackage({ selected_entry_ids: [ENTRY_A, 'doc-1'] }),
      makeInputs()
    )

    expect(result).toBeNull()
    expect(mockFetch).not.toHaveBeenCalled()
    expect(errors.value.join(' ')).toContain('doc-1')
  })

  it('surfaces a backend rejection instead of exporting a lock', async () => {
    mockFetch.mockResolvedValueOnce(
      createFetchResponse(
        { detail: 'Only approved/resolved knowledge can enter a governed context.' },
        false,
        400,
        'Bad Request'
      )
    )
    const { exportContextLock, lock, errors } = useContextAssemblyLock()

    const result = await exportContextLock(makePackage(), makeInputs())

    expect(result).toBeNull()
    expect(lock.value).toBeNull()
    expect(errors.value).toEqual(['Only approved/resolved knowledge can enter a governed context.'])
  })
})
