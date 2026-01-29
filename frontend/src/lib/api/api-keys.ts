import apiClient from './client'

// Types for API keys
export interface ApiKeyStatus {
  configured: Record<string, boolean>
  source: Record<string, string>
}

export interface EnvStatus {
  [provider: string]: boolean
}

export interface SetApiKeyRequest {
  api_key?: string
  base_url?: string
  endpoint?: string
  api_version?: string
  endpoint_llm?: string
  endpoint_embedding?: string
  endpoint_stt?: string
  endpoint_tts?: string
  service_type?: 'llm' | 'embedding' | 'stt' | 'tts'
  // Vertex AI specific fields
  vertex_project?: string
  vertex_location?: string
  vertex_credentials_path?: string
}

export interface MigrationResult {
  message: string
  migrated: string[]
  skipped: string[]
  errors: string[]
}

export interface TestConnectionResult {
  provider: string
  success: boolean
  message: string
}

export const apiKeysApi = {
  /**
   * Get the status of all configured API keys
   */
  getStatus: async (): Promise<ApiKeyStatus> => {
    const response = await apiClient.get<ApiKeyStatus>('/api-keys/status')
    return response.data
  },

  /**
   * Get status of environment variable API keys
   */
  getEnvStatus: async (): Promise<EnvStatus> => {
    const response = await apiClient.get<EnvStatus>('/api-keys/env-status')
    return response.data
  },

  /**
   * Set or update an API key for a provider
   */
  setKey: async (provider: string, data: SetApiKeyRequest): Promise<{ message: string }> => {
    const response = await apiClient.post<{ message: string }>(`/api-keys/${provider}`, data)
    return response.data
  },

  /**
   * Delete an API key for a provider
   */
  deleteKey: async (provider: string, serviceType?: string): Promise<{ message: string }> => {
    const url = serviceType
      ? `/api-keys/${provider}?service_type=${serviceType}`
      : `/api-keys/${provider}`
    const response = await apiClient.delete<{ message: string }>(url)
    return response.data
  },

  /**
   * Migrate API keys from environment variables to database
   */
  migrate: async (): Promise<MigrationResult> => {
    const response = await apiClient.post<MigrationResult>('/api-keys/migrate')
    return response.data
  },

  /**
   * Test connection for a provider
   */
  testConnection: async (provider: string): Promise<TestConnectionResult> => {
    const response = await apiClient.post<TestConnectionResult>(`/api-keys/${provider}/test`)
    return response.data
  },
}
