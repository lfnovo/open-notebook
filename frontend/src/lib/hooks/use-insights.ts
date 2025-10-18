import { useQuery } from '@tanstack/react-query'
import { insightsApi } from '@/lib/api/insights'

export function useInsight(id: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ['insights', id],
    queryFn: () => insightsApi.get(id),
    enabled: options?.enabled !== false && !!id,
    staleTime: 30 * 1000, // 30 seconds
  })
}
