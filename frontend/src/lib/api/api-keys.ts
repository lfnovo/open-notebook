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

// ============================================================================
// Provider Config Types (Multi-Config Support)
// ============================================================================

/**
 * A single provider configuration item
 */
export interface ProviderCredential {
  id: string
  name: string
  provider: string
  is_default: boolean
  api_key?: string  // Never returned from API (security)
  base_url?: string
  model?: string
  api_version?: string
  endpoint?: string
  endpoint_llm?: string
  endpoint_embedding?: string
  endpoint_stt?: string
  endpoint_tts?: string
  project?: string
  location?: string
  credentials_path?: string
  created?: string
  updated?: string
}

/**
 * Request to create a new provider configuration
 */
export interface CreateProviderConfigRequest {
  name: string
  api_key?: string
  base_url?: string
  model?: string
  api_version?: string
  endpoint?: string
  endpoint_llm?: string
  endpoint_embedding?: string
  endpoint_stt?: string
  endpoint_tts?: string
  project?: string
  location?: string
  credentials_path?: string
  is_default?: boolean
}

/**
 * Request to update an existing provider configuration
 */
export interface UpdateProviderConfigRequest {
  name?: string
  api_key?: string
  base_url?: string
  model?: string
  api_version?: string
  endpoint?: string
  endpoint_llm?: string
  endpoint_embedding?: string
  endpoint_stt?: string
  endpoint_tts?: string
  project?: string
  location?: string
  credentials_path?: string
}

/**
 * Response for listing provider configurations for a specific provider
 */
export interface ProviderConfigsListResponse {
  provider: string
  configs: ProviderCredential[]
  default_config_id?: string
}

/**
 * Response for listing all provider configurations
 */
export interface ProviderConfigsResponse {
  [provider: string]: ProviderCredential[]
}

// ============================================================================
// Legacy API Keys (Backward Compatibility)
// ============================================================================

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

// ============================================================================
// Provider Configs API (New Multi-Config Endpoints)
// ============================================================================

export const providerConfigsApi = {
  /**
   * List all provider configurations
   */
  listAllConfigs: async (): Promise<ProviderConfigsResponse> => {
    const response = await apiClient.get<ProviderConfigsResponse>('/api-keys/configs')
    return response.data
  },

  /**
   * List all configurations for a specific provider
   */
  listConfigs: async (provider: string): Promise<ProviderCredential[]> => {
    const response = await apiClient.get<ProviderConfigsListResponse>(
      `/api-keys/configs/${provider}`
    )
    return response.data.configs
  },

  /**
   * Get a specific configuration by ID
   */
  getConfig: async (provider: string, configId: string): Promise<ProviderCredential> => {
    const response = await apiClient.get<ProviderCredential>(`/api-keys/configs/${provider}/${configId}`)
    return response.data
  },

  /**
   * Create a new configuration for a provider
   */
  createConfig: async (
    provider: string,
    data: CreateProviderConfigRequest
  ): Promise<ProviderCredential> => {
    const response = await apiClient.post<ProviderCredential>(`/api-keys/configs/${provider}`, data)
    return response.data
  },

  /**
   * Update an existing configuration
   */
  updateConfig: async (
    provider: string,
    configId: string,
    data: UpdateProviderConfigRequest
  ): Promise<ProviderCredential> => {
    const response = await apiClient.put<ProviderCredential>(
      `/api-keys/configs/${provider}/${configId}`,
      data
    )
    return response.data
  },

  /**
   * Delete a configuration
   */
  deleteConfig: async (provider: string, configId: string): Promise<{ message: string }> => {
    const response = await apiClient.delete<{ message: string }>(
      `/api-keys/configs/${provider}/${configId}`
    )
    return response.data
  },

  /**
   * Set a configuration as the default for its provider
   */
  setDefault: async (provider: string, configId: string): Promise<{ message: string }> => {
    const response = await apiClient.put<{ message: string }>(
      `/api-keys/configs/${provider}/${configId}/default`
    )
    return response.data
  },
}
