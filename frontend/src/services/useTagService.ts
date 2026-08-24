import { useApi } from './useAPI'
import type { Tag } from '@/types/entry'

export function useTagService() {
  function listTags(): Promise<{ tags: Tag[]; count: number }> {
    return useApi<{ tags: Tag[]; count: number }>().makeRequest.get('/api/tags')
  }

  function createTag(name: string): Promise<Tag> {
    return useApi<Tag>().makeRequest.post('/api/tags', { body: { name } })
  }

  function updateTag(id: string, name: string): Promise<Tag> {
    return useApi<Tag>().makeRequest.patch(`/api/tags/${id}`, { body: { name } })
  }

  function deleteTag(id: string): Promise<void> {
    return useApi<void>().makeRequest.delete(`/api/tags/${id}`)
  }

  function listEntryTags(
    entryId: string
  ): Promise<{ entry_id: string; tags: Tag[]; count: number }> {
    return useApi<{ entry_id: string; tags: Tag[]; count: number }>().makeRequest.get(
      `/api/entries/${entryId}/tags`
    )
  }

  function addEntryTag(entryId: string, name: string): Promise<Tag> {
    return useApi<Tag>().makeRequest.post(`/api/entries/${entryId}/tags`, { body: { name } })
  }

  function removeEntryTag(entryId: string, tagId: string): Promise<void> {
    return useApi<void>().makeRequest.delete(`/api/entries/${entryId}/tags/${tagId}`)
  }

  return { listTags, createTag, updateTag, deleteTag, listEntryTags, addEntryTag, removeEntryTag }
}
