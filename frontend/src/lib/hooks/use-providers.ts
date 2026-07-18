import { useQuery } from '@tanstack/react-query'
import { providersApi } from '@/lib/api/providers'

export const PROVIDER_QUERY_KEYS = {
  providers: ['providers'] as const,
}

/**
 * Hook to list all supported AI providers (from the backend provider
 * registry). The list only changes on deploy, so cache it aggressively:
 * never stale within the session, kept in cache for a day.
 */
export function useProviders() {
  return useQuery({
    queryKey: PROVIDER_QUERY_KEYS.providers,
    queryFn: () => providersApi.list(),
    staleTime: Infinity,
    gcTime: 24 * 60 * 60 * 1000,
  })
}
