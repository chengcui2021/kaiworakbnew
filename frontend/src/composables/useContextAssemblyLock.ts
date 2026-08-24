import { ref } from 'vue'
import { useGovernedContextService } from '@/services/useGovernedContextService'
import type { ContextPackage } from '@/types/domain'
import type {
  ContextAssemblyLock,
  GovernanceRuleInput,
  GovernedContextRequest,
} from '@/types/governedContext'

/**
 * Turns a context package plus the operator-supplied governed inputs into a
 * real Context Assembly Lock produced by `/api/governed-context/lock`.
 *
 * Before MDSU-345 the pages assembled a lock object in the browser with a
 * `checksum: 'sha256:PLACEHOLDER'` field — it carried no repository,
 * requirement or governance context and no verifiable hash. The lock is now
 * always the backend's, so its `context_hash` is deterministic and its
 * `governed_inputs` identify what it was produced from.
 */
export type GovernedContextInputs = {
  requestTitle: string
  requestDescription: string
  repositoryName: string
  repositoryBranch: string
  repositoryCommitSha: string
  /** One `topic :: rule` statement per line. */
  governance: string
}

export function emptyGovernedContextInputs(): GovernedContextInputs {
  return {
    requestTitle: '',
    requestDescription: '',
    repositoryName: '',
    repositoryBranch: '',
    repositoryCommitSha: '',
    governance: '',
  }
}

const COMMIT_SHA_RE = /^[0-9a-f]{7,64}$/i
const KB_ENTRY_ID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

/**
 * Split a package's selection into persistent KB entry ids and everything
 * else. Workspace documents live in the workspace store, not the KB, so they
 * are not eligible governed knowledge — they are reported, never dropped
 * silently, so the lock's knowledge lineage stays complete.
 */
export function partitionKnowledgeIds(ids: string[]): {
  entryIds: string[]
  ineligibleIds: string[]
} {
  return {
    entryIds: ids.filter((id) => KB_ENTRY_ID_RE.test(id)),
    ineligibleIds: ids.filter((id) => !KB_ENTRY_ID_RE.test(id)),
  }
}

/**
 * Parse `topic :: rule` lines into governance rule inputs. A line without a
 * `::` separator is its own topic and statement. Rules are submitted as
 * approved — the backend still detects conflicting statements on one topic.
 */
export function parseGovernanceRules(text: string): GovernanceRuleInput[] {
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line, index) => {
      const [rawTopic, ...rest] = line.split('::')
      const topic = rawTopic.trim() || line
      const rule = rest.join('::').trim() || line
      return {
        id: `gov-${index + 1}`,
        title: topic,
        topic,
        rule,
        status: 'approved',
        precedence: 0,
      }
    })
}

export function validateGovernedContextInputs(inputs: GovernedContextInputs): string[] {
  const errors: string[] = []
  if (!inputs.requestTitle.trim()) errors.push('An engineering request title is required.')
  if (!inputs.requestDescription.trim()) {
    errors.push('An engineering request description is required.')
  }
  if (!inputs.repositoryName.trim()) errors.push('A repository name is required.')
  if (!COMMIT_SHA_RE.test(inputs.repositoryCommitSha.trim())) {
    errors.push('The repository commit SHA must be 7-64 hexadecimal characters.')
  }
  return errors
}

export function buildGovernedContextRequest(
  pkg: ContextPackage,
  inputs: GovernedContextInputs
): GovernedContextRequest {
  const { entryIds } = partitionKnowledgeIds(pkg.selected_entry_ids)
  return {
    request: {
      title: inputs.requestTitle.trim(),
      description: inputs.requestDescription.trim(),
      source: `metamorphic-kb:workspace/${pkg.workspace_id}/package/${pkg.id}`,
    },
    repository: {
      name: inputs.repositoryName.trim(),
      branch: inputs.repositoryBranch.trim() || undefined,
      commit_sha: inputs.repositoryCommitSha.trim(),
    },
    knowledge: { entry_ids: entryIds },
    governance: parseGovernanceRules(inputs.governance),
  }
}

export function downloadContextLock(
  lock: ContextAssemblyLock,
  filename = 'context-assembly-lock.json'
): void {
  const blob = new Blob([JSON.stringify(lock, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export function useContextAssemblyLock() {
  const { createContextAssemblyLock } = useGovernedContextService()

  const lock = ref<ContextAssemblyLock | null>(null)
  const exporting = ref(false)
  const errors = ref<string[]>([])

  async function exportContextLock(
    pkg: ContextPackage,
    inputs: GovernedContextInputs
  ): Promise<ContextAssemblyLock | null> {
    const problems = validateGovernedContextInputs(inputs)
    const { entryIds, ineligibleIds } = partitionKnowledgeIds(pkg.selected_entry_ids)
    if (ineligibleIds.length) {
      problems.push(
        `Not persistent KB knowledge, so it cannot enter a governed context: ${ineligibleIds.join(', ')}.`
      )
    }
    if (!entryIds.length && !ineligibleIds.length) {
      problems.push('This package selects no approved KB entries.')
    }
    errors.value = problems
    if (problems.length) return null

    exporting.value = true
    try {
      const created = await createContextAssemblyLock(buildGovernedContextRequest(pkg, inputs))
      lock.value = created
      downloadContextLock(created)
      return created
    } catch (err) {
      errors.value = [
        err instanceof Error ? err.message : 'Failed to create the context assembly lock',
      ]
      return null
    } finally {
      exporting.value = false
    }
  }

  function reset(): void {
    lock.value = null
    errors.value = []
  }

  return { lock, exporting, errors, exportContextLock, reset }
}
