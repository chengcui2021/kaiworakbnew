import { useApi } from './useAPI'
import type { ApprovalStatus, KbDocument } from '@/types/domain'

export function useDocumentService() {
  function listDocuments(
    workspaceId: string,
    approvalStatus?: ApprovalStatus | string
  ): Promise<KbDocument[]> {
    const query = approvalStatus
      ? `?${new URLSearchParams({ approval_status: approvalStatus }).toString()}`
      : ''
    return useApi<KbDocument[]>().makeRequest.get(
      `/api/workspaces/${workspaceId}/documents${query}`
    )
  }

  function createDocument(
    workspaceId: string,
    payload: { title: string; content?: string }
  ): Promise<KbDocument> {
    return useApi<KbDocument>().makeRequest.post(`/api/workspaces/${workspaceId}/documents`, {
      body: { title: payload.title, content: payload.content || '' },
    })
  }

  function deleteDocument(
    workspaceId: string,
    documentId: string
  ): Promise<{ id: string; deleted: boolean }> {
    return useApi<{ id: string; deleted: boolean }>().makeRequest.delete(
      `/api/workspaces/${workspaceId}/documents/${documentId}`
    )
  }

  function moveDocument(
    workspaceId: string,
    documentId: string,
    targetWorkspaceId: string
  ): Promise<KbDocument> {
    return useApi<KbDocument>().makeRequest.post(
      `/api/workspaces/${workspaceId}/documents/${documentId}/move`,
      { body: { target_workspace_id: targetWorkspaceId } }
    )
  }

  function setDocumentStatus(
    workspaceId: string,
    documentId: string,
    approvalStatus: ApprovalStatus | string
  ): Promise<KbDocument> {
    return useApi<KbDocument>().makeRequest.put(
      `/api/workspaces/${workspaceId}/documents/${documentId}/status`,
      { body: { approval_status: approvalStatus } }
    )
  }

  return { listDocuments, createDocument, deleteDocument, moveDocument, setDocumentStatus }
}
