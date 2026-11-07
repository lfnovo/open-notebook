import apiClient from './client'
import type {
  DiscoverSourcesRequest,
  DiscoverSourcesResponse,
} from '@/lib/types/discover'

export const discoverApi = {
  discoverSources: async (input: DiscoverSourcesRequest) => {
    const response = await apiClient.post<DiscoverSourcesResponse>(
      '/sources/discover',
      input
    )
    return response.data
  },
}
