import { useApi } from './useAPI'
import type { GitHubIngestionPayload, GitHubIngestionResult } from '@/types/ingestion'

export function useIngestionService() {
  function ingestGitHub(payload: GitHubIngestionPayload): Promise<GitHubIngestionResult> {
    return useApi<GitHubIngestionResult>().makeRequest.post('/api/ingestion/github', { body: payload })
  }
  function ingestText(payload: { title: string; content: string; source_label?: string; source_type?: string; workstream_id?: string | null; author?: string }): Promise<any> {
    return useApi<any>().makeRequest.post('/api/ingestion/text', { body: payload })
  }
  function ingestUrl(payload: { url: string; workstream_id?: string | null; author?: string }): Promise<any> {
    return useApi<any>().makeRequest.post('/api/ingestion/url', { body: payload })
  }
  return { ingestGitHub, ingestText, ingestUrl }
}
