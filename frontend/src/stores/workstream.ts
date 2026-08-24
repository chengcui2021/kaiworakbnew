import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { useWorkstreamService } from '@/services/useWorkstreamService'
import type { Workstream } from '@/types/domain'

const ACTIVE_WORKSTREAM_KEY = 'kb.activeWorkstreamId'

export const useWorkstreamStore = defineStore('workstream', () => {
  const workstreams = ref<Workstream[]>([])
  const activeWorkstreamId = ref<string | null>(localStorage.getItem(ACTIVE_WORKSTREAM_KEY))
  const loading = ref(false)
  const error = ref<string | null>(null)

  const activeWorkstream = computed<Workstream | null>(
    () => workstreams.value.find((w) => w.id === activeWorkstreamId.value) || null
  )

  async function loadWorkstreams(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      workstreams.value = await useWorkstreamService().listWorkstreams()
      // Restore / repair the active selection.
      if (
        !activeWorkstreamId.value ||
        !workstreams.value.some((w) => w.id === activeWorkstreamId.value)
      ) {
        setActiveWorkstream(workstreams.value[0]?.id ?? null)
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to load workstreams'
    } finally {
      loading.value = false
    }
  }

  function setActiveWorkstream(id: string | null): void {
    activeWorkstreamId.value = id
    if (id) {
      localStorage.setItem(ACTIVE_WORKSTREAM_KEY, id)
    } else {
      localStorage.removeItem(ACTIVE_WORKSTREAM_KEY)
    }
  }

  return {
    workstreams,
    activeWorkstreamId,
    activeWorkstream,
    loading,
    error,
    loadWorkstreams,
    setActiveWorkstream,
  }
})
