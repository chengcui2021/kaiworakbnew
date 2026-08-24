import { useApi } from './useAPI'
import type {
  ContextAssemblyLock,
  GovernedContextAssembly,
  GovernedContextRequest,
  LockStatusResponse,
} from '@/types/governedContext'

const BASE = '/api/governed-context'

/**
 * The backend rejects unresolvable governance with 409 and a *structured*
 * detail body; `useAPI` only surfaces string `detail`s, so 409 would otherwise
 * degrade to "Request failed: Conflict". Map it here rather than losing the
 * fact that the conflict was detected instead of silently accepted.
 */
const GOVERNED_ERROR_MAP: Record<number, string> = {
  409: 'Conflicting engineering governance inputs — the assembly was rejected rather than silently accepting them.',
}

/**
 * Governed Context Assembly (MDSU-345). Requirement, repository, approved
 * knowledge and engineering governance are combined by the backend into one
 * assembly with a deterministic context hash, which can then be frozen into a
 * Context Assembly Lock.
 */
export function useGovernedContextService() {
  function assembleGovernedContext(
    payload: GovernedContextRequest
  ): Promise<GovernedContextAssembly> {
    return useApi<GovernedContextAssembly>().makeRequest.post(`${BASE}/assemble`, {
      body: payload,
      errorMap: GOVERNED_ERROR_MAP,
    })
  }

  function createContextAssemblyLock(
    payload: GovernedContextRequest
  ): Promise<ContextAssemblyLock> {
    return useApi<ContextAssemblyLock>().makeRequest.post(`${BASE}/lock`, {
      body: payload,
      errorMap: GOVERNED_ERROR_MAP,
    })
  }

  /** Is `lock` still valid for the current governed inputs, and if not, why? */
  function checkContextAssemblyLock(
    lock: ContextAssemblyLock,
    current: GovernedContextRequest
  ): Promise<LockStatusResponse> {
    return useApi<LockStatusResponse>().makeRequest.post(`${BASE}/lock/status`, {
      body: { lock, current },
      errorMap: GOVERNED_ERROR_MAP,
    })
  }

  return { assembleGovernedContext, createContextAssemblyLock, checkContextAssemblyLock }
}
