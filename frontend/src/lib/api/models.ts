import apiClient from './client'
import {
  Model,
  CreateModelRequest,
  ModelDefaults,
  ProviderAvailability,
  DiscoveredModel,
  ProviderSyncResult,
  AllProvidersSyncResult,
  ProviderModelCount,
  AutoAssignResult,
} from '@/lib/types/models'

export const modelsApi = {
  list: async () => {
    const response = await apiClient.get<Model[]>('/models')
    return response.data
  },

  get: async (id: string) => {
    const response = await apiClient.get<Model>(`/models/${id}`)
    return response.data
  },

  create: async (data: CreateModelRequest) => {
    const response = await apiClient.post<Model>('/models', data)
    return response.data
  },

  delete: async (id: string) => {
    await apiClient.delete(`/models/${id}`)
  },

  getDefaults: async () => {
    const response = await apiClient.get<ModelDefaults>('/models/defaults')
    return response.data
  },

  updateDefaults: async (data: Partial<ModelDefaults>) => {
    const response = await apiClient.put<ModelDefaults>('/models/defaults', data)
    return response.data
  },

  getProviders: async () => {
    const response = await apiClient.get<ProviderAvailability>('/models/providers')
    return response.data
  },

  // Model Discovery API
  /**
   * Discover available models from a provider without registering them
   */
  discoverModels: async (provider: string) => {
    const response = await apiClient.get<DiscoveredModel[]>(`/models/discover/${provider}`)
    return response.data
  },

  /**
   * Sync models for a specific provider (discover and register)
   */
  syncProvider: async (provider: string) => {
    const response = await apiClient.post<ProviderSyncResult>(`/models/sync/${provider}`)
    return response.data
  },

  /**
   * Sync models for all configured providers
   */
  syncAll: async () => {
    const response = await apiClient.post<AllProvidersSyncResult>('/models/sync')
    return response.data
  },

  /**
   * Get count of registered models for a provider
   */
  getProviderModelCount: async (provider: string) => {
    const response = await apiClient.get<ProviderModelCount>(`/models/count/${provider}`)
    return response.data
  },

  /**
   * Get all models for a specific provider
   */
  getByProvider: async (provider: string) => {
    const response = await apiClient.get<Model[]>(`/models/by-provider/${provider}`)
    return response.data
  },

  /**
   * Auto-assign default models based on available models
   */
  autoAssign: async () => {
    const response = await apiClient.post<AutoAssignResult>('/models/auto-assign')
    return response.data
  },
}