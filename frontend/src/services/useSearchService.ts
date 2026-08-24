import { useApi } from './useAPI'
import type { SearchResponse } from '@/types/domain'

export function useSearchService() {
  function searchDocuments(workspaceId: string, query: string): Promise<SearchResponse> {
    const params = new URLSearchParams({ workspace_id: workspaceId, q: query })
    return useApi<SearchResponse>().makeRequest.get(`/api/search?${params.toString()}`)
  }

  return { searchDocuments }
}
