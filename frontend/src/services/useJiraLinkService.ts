import { useApi } from './useAPI'
import type { JiraLinksListResponse } from '@/types/entry'

export function useJiraLinkService() {
  function listJiraLinks(entryId: string): Promise<JiraLinksListResponse> {
    return useApi<JiraLinksListResponse>().makeRequest.get(`/api/entries/${entryId}/jira-links`)
  }

  function addJiraLink(
    entryId: string,
    jiraKey: string
  ): Promise<JiraLinksListResponse['links'][number]> {
    return useApi<JiraLinksListResponse['links'][number]>().makeRequest.post(
      `/api/entries/${entryId}/jira-links`,
      { body: { jira_key: jiraKey } }
    )
  }

  function removeJiraLink(entryId: string, jiraKey: string): Promise<void> {
    return useApi<void>().makeRequest.delete(
      `/api/entries/${entryId}/jira-links/${encodeURIComponent(jiraKey)}`
    )
  }

  return { listJiraLinks, addJiraLink, removeJiraLink }
}
