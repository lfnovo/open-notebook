import { useQuery } from '@tanstack/react-query'
import { capabilitiesApi } from '@/lib/api/capabilities'

export const CAPABILITIES_QUERY_KEYS = {
  capabilities: ['capabilities'] as const,
}

/**
 * Hook reporting which opt-in extraction runtimes (Docling, Crawl4AI local) are
 * available. These only change when the container is restarted with different
 * OPEN_NOTEBOOK_ENABLE_* flags, so cache aggressively like the providers list.
 */
export function useCapabilities() {
  return useQuery({
    queryKey: CAPABILITIES_QUERY_KEYS.capabilities,
    queryFn: () => capabilitiesApi.get(),
    staleTime: Infinity,
    gcTime: 24 * 60 * 60 * 1000,
  })
}
