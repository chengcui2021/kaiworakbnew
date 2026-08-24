import { useApi } from './useAPI'
import type { ContextPackage } from '@/types/domain'

export function usePackageService() {
  function listContextPackages(workspaceId: string): Promise<ContextPackage[]> {
    return useApi<ContextPackage[]>().makeRequest.get(`/api/workspaces/${workspaceId}/packages`)
  }

  function createContextPackage(
    workspaceId: string,
    payload: { name: string; selected_entry_ids: string[] }
  ): Promise<ContextPackage> {
    return useApi<ContextPackage>().makeRequest.post(`/api/workspaces/${workspaceId}/packages`, {
      body: payload,
    })
  }

  return { listContextPackages, createContextPackage }
}
