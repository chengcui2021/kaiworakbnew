import { storeToRefs } from 'pinia'
import { useWorkstreamStore } from '@/stores/workstream'

export function useWorkstream() {
  const store = useWorkstreamStore()
  const { workstreams, activeWorkstreamId, activeWorkstream, loading, error } = storeToRefs(store)
  return {
    workstreams,
    activeWorkstreamId,
    activeWorkstream,
    loading,
    error,
    loadWorkstreams: store.loadWorkstreams,
    setActiveWorkstream: store.setActiveWorkstream,
  }
}
