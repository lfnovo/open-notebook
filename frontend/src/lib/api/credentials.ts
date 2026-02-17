import apiClient from './client'

// Types for credentials API
export interface Credential {
  id: string
  name: string
  provider: string
  modalities: string[]
  base_url?: string | null
  endpoint?: string | null
  api_version?: string | null
  endpoint_llm?: string | null
  endpoint_embedding?: string | null
  endpoint_stt?: string | null
  endpoint_tts?: string | null
  project?: string | null
  location?: string | null
  credentials_path?: string | null
  has_api_key: boolean
  created: string
  updated: string
  model_count: number
}

export interface CreateCredentialRequest {
  name: string
  provider: string
  modalities: string[]
  api_key?: string
  base_url?: string
  endpoint?: string
  api_version?: string
  endpoint_llm?: string
  endpoint_embedding?: string
  endpoint_stt?: string
  endpoint_tts?: string
  project?: string
  location?: string
  credentials_path?: string
}

export interface UpdateCredentialRequest {
  name?: string
  modalities?: string[]
  api_key?: string
  base_url?: string
  endpoint?: string
  api_version?: string
  endpoint_llm?: string
  endpoint_embedding?: string
  endpoint_stt?: string
  endpoint_tts?: string
  project?: string
  location?: string
  credentials_path?: string
}

export interface DiscoveredModel {
  name: string
  provider: string
  model_type?: string
  description?: string
}

export interface RegisterModelData {
  name: string
  provider: string
  model_type: string
}

export interface DiscoverModelsResponse {
  credential_id: string
  provider: string
  discovered: DiscoveredModel[]
}

export interface RegisterModelsRequest {
  models: RegisterModelData[]
}

export interface RegisterModelsResponse {
  created: number
  existing: number
}

export interface TestConnectionResult {
  provider: string
  success: boolean
  message: string
}

export interface CredentialDeleteResponse {
  message: string
  deleted_models: number
}

export interface MigrationResult {
  message: string
  migrated: string[]
  skipped: string[]
  not_configured?: string[]
  errors: string[]
}

export interface CredentialStatus {
  configured: Record<string, boolean>
  source: Record<string, string>
  encryption_configured: boolean
}

export type EnvStatus = Record<string, boolean>

export const credentialsApi = {
  /**
   * Get configuration status for all providers
   */
  getStatus: async (): Promise<CredentialStatus> => {
    const response = await apiClient.get<CredentialStatus>('/credentials/status')
    return response.data
  },

  /**
   * Get environment variable status for all providers
   */
  getEnvStatus: async (): Promise<EnvStatus> => {
    const response = await apiClient.get<EnvStatus>('/credentials/env-status')
    return response.data
  },

  /**
   * List all credentials, optionally filtered by provider
   */
  list: async (provider?: string): Promise<Credential[]> => {
    const params = provider ? { provider } : {}
    const response = await apiClient.get<Credential[]>('/credentials', { params })
    return response.data
  },

  /**
   * List credentials for a specific provider
   */
  listByProvider: async (provider: string): Promise<Credential[]> => {
    const response = await apiClient.get<Credential[]>(`/credentials/by-provider/${provider}`)
    return response.data
  },

  /**
   * Get a specific credential by ID
   */
  get: async (credentialId: string): Promise<Credential> => {
    const response = await apiClient.get<Credential>(`/credentials/${credentialId}`)
    return response.data
  },

  /**
   * Create a new credential
   */
  create: async (data: CreateCredentialRequest): Promise<Credential> => {
    const response = await apiClient.post<Credential>('/credentials', data)
    return response.data
  },

  /**
   * Update an existing credential
   */
  update: async (credentialId: string, data: UpdateCredentialRequest): Promise<Credential> => {
    const response = await apiClient.put<Credential>(`/credentials/${credentialId}`, data)
    return response.data
  },

  /**
   * Delete a credential
   */
  delete: async (
    credentialId: string,
    options?: { delete_models?: boolean; migrate_to?: string }
  ): Promise<CredentialDeleteResponse> => {
    const params: Record<string, string | boolean> = {}
    if (options?.delete_models) params.delete_models = true
    if (options?.migrate_to) params.migrate_to = options.migrate_to
    const response = await apiClient.delete<CredentialDeleteResponse>(
      `/credentials/${credentialId}`,
      { params }
    )
    return response.data
  },

  /**
   * Test connection for a credential
   */
  test: async (credentialId: string): Promise<TestConnectionResult> => {
    const response = await apiClient.post<TestConnectionResult>(
      `/credentials/${credentialId}/test`
    )
    return response.data
  },

  /**
   * Discover models using a credential's API key
   */
  discover: async (credentialId: string): Promise<DiscoverModelsResponse> => {
    const response = await apiClient.post<DiscoverModelsResponse>(
      `/credentials/${credentialId}/discover`
    )
    return response.data
  },

  /**
   * Register discovered models and link them to a credential
   */
  registerModels: async (
    credentialId: string,
    data: RegisterModelsRequest
  ): Promise<RegisterModelsResponse> => {
    const response = await apiClient.post<RegisterModelsResponse>(
      `/credentials/${credentialId}/register-models`,
      data
    )
    return response.data
  },

  /**
   * Migrate from ProviderConfig to individual credentials
   */
  migrateFromProviderConfig: async (): Promise<MigrationResult> => {
    const response = await apiClient.post<MigrationResult>(
      '/credentials/migrate-from-provider-config'
    )
    return response.data
  },

  /**
   * Migrate from environment variables to credentials
   */
  migrateFromEnv: async (): Promise<MigrationResult> => {
    const response = await apiClient.post<MigrationResult>('/credentials/migrate-from-env')
    return response.data
  },
}
