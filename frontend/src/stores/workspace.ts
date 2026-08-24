import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { useWorkspaceService } from '@/services/useWorkspaceService'
import type { Workspace } from '@/types/domain'

const ACTIVE_WORKSPACE_KEY = 'kb.activeWorkspaceId'

export const useWorkspaceStore = defineStore('workspace', () => {
  const workspaces = ref<Workspace[]>([])
  const activeWorkspaceId = ref<string | null>(localStorage.getItem(ACTIVE_WORKSPACE_KEY))
  const loading = ref(false)
  const error = ref<string | null>(null)

  const activeWorkspace = computed<Workspace | null>(
    () => workspaces.value.find((w) => w.id === activeWorkspaceId.value) || null
  )

  async function loadWorkspaces(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      workspaces.value = await useWorkspaceService().listWorkspaces()
      // Restore / repair the active selection.
      if (
        !activeWorkspaceId.value ||
        !workspaces.value.some((w) => w.id === activeWorkspaceId.value)
      ) {
        setActiveWorkspace(workspaces.value[0]?.id ?? null)
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to load workspaces'
    } finally {
      loading.value = false
    }
  }

  function setActiveWorkspace(id: string | null): void {
    activeWorkspaceId.value = id
    if (id) {
      localStorage.setItem(ACTIVE_WORKSPACE_KEY, id)
    } else {
      localStorage.removeItem(ACTIVE_WORKSPACE_KEY)
    }
  }

  return {
    workspaces,
    activeWorkspaceId,
    activeWorkspace,
    loading,
    error,
    loadWorkspaces,
    setActiveWorkspace,
  }
})
