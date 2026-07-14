import apiClient from './client'
import { Capabilities } from '@/lib/types/api'

export const capabilitiesApi = {
  /**
   * Report which opt-in heavy extraction runtimes (Docling, Crawl4AI local)
   * are actually available in the running container.
   */
  get: async (): Promise<Capabilities> => {
    const response = await apiClient.get<Capabilities>('/capabilities')
    return response.data
  },
}
