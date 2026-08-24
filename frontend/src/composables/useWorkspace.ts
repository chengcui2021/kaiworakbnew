import { storeToRefs } from 'pinia'
import { useWorkspaceStore } from '@/stores/workspace'

export function useWorkspace() {
  const store = useWorkspaceStore()
  const { workspaces, activeWorkspaceId, activeWorkspace, loading, error } = storeToRefs(store)
  return {
    workspaces,
    activeWorkspaceId,
    activeWorkspace,
    loading,
    error,
    loadWorkspaces: store.loadWorkspaces,
    setActiveWorkspace: store.setActiveWorkspace,
  }
}
