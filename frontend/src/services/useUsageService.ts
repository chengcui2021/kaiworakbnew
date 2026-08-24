import { useApi } from './useAPI'
import type { UsageSummary } from '@/types/usage'

export function useUsageService() {
  function getUsageSummary(): Promise<UsageSummary> {
    return useApi<UsageSummary>().makeRequest.get('/api/llm-usage/summary')
  }

  return { getUsageSummary }
}
