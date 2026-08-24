import { useApi } from './useAPI'
import type {
  Workspace,
  WorkspaceActivity,
  WorkspaceStats,
  WorkspaceValidationResult,
} from '@/types/domain'

export function useWorkspaceService() {
  function listWorkspaces(): Promise<Workspace[]> {
    return useApi<Workspace[]>().makeRequest.get('/api/workspaces')
  }

  function getWorkspace(id: string): Promise<Workspace> {
    return useApi<Workspace>().makeRequest.get(`/api/workspaces/${id}`)
  }

  function createWorkspace(payload: { name: string; description?: string }): Promise<Workspace> {
    return useApi<Workspace>().makeRequest.post('/api/workspaces', {
      body: { name: payload.name, description: payload.description || '' },
    })
  }

  function updateWorkspace(
    id: string,
    payload: { name?: string; description?: string }
  ): Promise<Workspace> {
    return useApi<Workspace>().makeRequest.put(`/api/workspaces/${id}`, { body: payload })
  }

  function deleteWorkspace(id: string): Promise<{ id: string; deleted: boolean }> {
    return useApi<{ id: string; deleted: boolean }>().makeRequest.delete(`/api/workspaces/${id}`)
  }

  function getWorkspaceStats(id: string): Promise<WorkspaceStats> {
    return useApi<WorkspaceStats>().makeRequest.get(`/api/workspaces/${id}/stats`)
  }

  function validateWorkspace(id: string): Promise<WorkspaceValidationResult> {
    return useApi<WorkspaceValidationResult>().makeRequest.get(`/api/workspaces/${id}/validate`)
  }

  function listActivities(workspaceId: string, limit = 20): Promise<WorkspaceActivity[]> {
    const params = new URLSearchParams({ limit: String(limit) })
    return useApi<WorkspaceActivity[]>().makeRequest.get(
      `/api/workspaces/${workspaceId}/activities?${params.toString()}`
    )
  }

  return {
    listWorkspaces,
    getWorkspace,
    createWorkspace,
    updateWorkspace,
    deleteWorkspace,
    getWorkspaceStats,
    validateWorkspace,
    listActivities,
  }
}
