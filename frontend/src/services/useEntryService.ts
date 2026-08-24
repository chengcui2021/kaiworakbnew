import { useApi } from './useAPI'
import type {
  Entry,
  EntryCreatePayload,
  EntryListFilters,
  EntryListResponse,
  EntryPatchStatus,
  EntrySearchFilters,
  EntrySearchResponse,
  EntryUpdatePayload,
} from '@/types/entry'

function buildQuery(params: Record<string, string | number | undefined>): string {
  const q = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') {
      q.set(key, String(value))
    }
  }
  const s = q.toString()
  return s ? `?${s}` : ''
}

export function useEntryService() {
  function listEntries(filters: EntryListFilters = {}): Promise<EntryListResponse> {
    const query = buildQuery({
      workstream_id: filters.workstream_id,
      unassigned: filters.unassigned ? 1 : undefined,
      component: filters.component,
      type: filters.type,
      status: filters.status,
      tag: filters.tag,
      limit: filters.limit,
      offset: filters.offset,
    })
    return useApi<EntryListResponse>().makeRequest.get(`/api/entries${query}`)
  }

  function getEntry(id: string): Promise<Entry> {
    return useApi<Entry>().makeRequest.get(`/api/entries/${id}`)
  }

  function createEntry(payload: EntryCreatePayload): Promise<Entry> {
    return useApi<Entry>().makeRequest.post('/api/entries', { body: payload })
  }

  function updateEntry(id: string, payload: EntryUpdatePayload): Promise<Entry> {
    return useApi<Entry>().makeRequest.put(`/api/entries/${id}`, { body: payload })
  }

  function patchEntryStatus(id: string, status: EntryPatchStatus): Promise<Entry> {
    return useApi<Entry>().makeRequest.patch(`/api/entries/${id}`, { body: { status } })
  }

  function deleteEntry(id: string): Promise<void> {
    return useApi<void>().makeRequest.delete(`/api/entries/${id}`)
  }

  function searchEntries(
    query: string,
    filters: EntrySearchFilters = {}
  ): Promise<EntrySearchResponse> {
    const q = buildQuery({
      q: query,
      workstream_id: filters.workstream_id,
      unassigned: filters.unassigned ? 1 : undefined,
      component: filters.component,
      type: filters.type,
      status: filters.status,
      tag: filters.tag,
      limit: filters.limit,
    })
    return useApi<EntrySearchResponse>().makeRequest.get(`/api/entries/search${q}`)
  }

  return {
    listEntries,
    getEntry,
    createEntry,
    updateEntry,
    patchEntryStatus,
    deleteEntry,
    searchEntries,
  }
}
