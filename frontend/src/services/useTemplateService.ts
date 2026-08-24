import { useApi } from './useAPI'
import type { Template } from '@/types/entry'

export function useTemplateService() {
  function listTemplates(): Promise<{ templates: Template[]; count: number }> {
    return useApi<{ templates: Template[]; count: number }>().makeRequest.get('/api/templates')
  }

  function getTemplate(id: string): Promise<Template> {
    return useApi<Template>().makeRequest.get(`/api/templates/${id}`)
  }

  function createTemplate(payload: { name: string; content: string }): Promise<Template> {
    return useApi<Template>().makeRequest.post('/api/templates', { body: payload })
  }

  function updateTemplate(
    id: string,
    payload: { name: string; content: string }
  ): Promise<Template> {
    return useApi<Template>().makeRequest.put(`/api/templates/${id}`, { body: payload })
  }

  function deleteTemplate(id: string): Promise<void> {
    return useApi<void>().makeRequest.delete(`/api/templates/${id}`)
  }

  return { listTemplates, getTemplate, createTemplate, updateTemplate, deleteTemplate }
}
