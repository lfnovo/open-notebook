import apiClient from './client'

// Types for providers API
export interface ProviderInfo {
  name: string
  display_name: string
  modalities: string[]
  docs_url?: string | null
  env_configured: boolean
}

export const providersApi = {
  /**
   * List all supported AI providers with their registry metadata.
   * The backend registry owns the display order.
   */
  list: async (): Promise<ProviderInfo[]> => {
    const response = await apiClient.get<ProviderInfo[]>('/providers')
    return response.data
  },
}
