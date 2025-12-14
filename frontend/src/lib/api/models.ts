import apiClient from './client'
import { Model, CreateModelRequest, ModelDefaults, ProviderAvailability } from '@/lib/types/models'

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

  getAvailableOllamaModels: async () => {
    const response = await apiClient.get<{
      available: boolean
      models: Array<{
        name: string
        size: number
        modified_at: string
        digest: string
      }>
      base_url: string
    }>('/models/ollama/available')
    return response.data
  },

  validateConfiguredModels: async () => {
    const response = await apiClient.get<{
      valid: boolean
      missing_models: Array<{
        type: string
        name: string
      }>
      available_ollama_models: string[]
      details: Record<string, {
        configured: string | null
        available: boolean | null
        provider: string
      }>
    }>('/models/validate')
    return response.data
  },

  syncOllamaModels: async () => {
    const response = await apiClient.post<{
      synced: number
      skipped: number
      total: number
    }>('/models/ollama/sync')
    return response.data
  }
}