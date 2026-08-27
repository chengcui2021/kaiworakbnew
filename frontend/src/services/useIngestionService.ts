import { useApi } from './useAPI'
import type { GitHubIngestionPayload, GitHubIngestionResult } from '@/types/ingestion'

export function useIngestionService() {
  function ingestGitHub(payload: GitHubIngestionPayload): Promise<GitHubIngestionResult> {
    return useApi<GitHubIngestionResult>().makeRequest.post('/api/ingestion/github', { body: payload })
  }
  return { ingestGitHub }
}
