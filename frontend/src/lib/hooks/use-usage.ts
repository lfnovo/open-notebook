import { useQuery } from '@tanstack/react-query'

import { usageApi } from '@/lib/api/usage'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { UsagePeriod } from '@/lib/types/usage'

/**
 * Spend changes infrequently (it's aggregated from LLM calls, not a live
 * feed), so a multi-minute staleTime plus refetch-on-focus is enough to
 * keep it reasonably fresh without polling.
 */
export function useUsageSummary(period: UsagePeriod = 'month') {
  return useQuery({
    queryKey: QUERY_KEYS.usageSummary(period),
    queryFn: () => usageApi.getSummary(period),
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: true,
  })
}
