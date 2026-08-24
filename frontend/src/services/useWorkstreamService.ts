import { useApi } from './useAPI'
import type { Workstream, WorkstreamStats, WorkstreamValidationResult } from '@/types/domain'

export function useWorkstreamService() {
  function listWorkstreams(): Promise<Workstream[]> {
    return useApi<Workstream[]>().makeRequest.get('/api/workstreams')
  }

  function getWorkstream(id: string): Promise<Workstream> {
    return useApi<Workstream>().makeRequest.get(`/api/workstreams/${id}`)
  }

  function createWorkstream(payload: { name: string; description?: string }): Promise<Workstream> {
    return useApi<Workstream>().makeRequest.post('/api/workstreams', {
      body: { name: payload.name, description: payload.description || '' },
    })
  }

  function updateWorkstream(
    id: string,
    payload: { name?: string; description?: string }
  ): Promise<Workstream> {
    return useApi<Workstream>().makeRequest.put(`/api/workstreams/${id}`, { body: payload })
  }

  function deleteWorkstream(id: string): Promise<{ id: string; deleted: boolean }> {
    return useApi<{ id: string; deleted: boolean }>().makeRequest.delete(`/api/workstreams/${id}`)
  }

  function getWorkstreamStats(id: string): Promise<WorkstreamStats> {
    return useApi<WorkstreamStats>().makeRequest.get(`/api/workstreams/${id}/stats`)
  }

  function validateWorkstream(id: string): Promise<WorkstreamValidationResult> {
    return useApi<WorkstreamValidationResult>().makeRequest.get(`/api/workstreams/${id}/validate`)
  }

  return {
    listWorkstreams,
    getWorkstream,
    createWorkstream,
    updateWorkstream,
    deleteWorkstream,
    getWorkstreamStats,
    validateWorkstream,
  }
}
