import apiClient from './client'
import { ModuleResponse, CreateModuleRequest, UpdateModuleRequest } from '@/lib/types/api'

export const modulesApi = {
  list: async (params?: { archived?: boolean; order_by?: string }) => {
    const response = await apiClient.get<ModuleResponse[]>('/modules', { params })
    return response.data
  },

  get: async (id: string) => {
    const response = await apiClient.get<ModuleResponse>(`/modules/${id}`)
    return response.data
  },

  create: async (data: CreateModuleRequest) => {
    const response = await apiClient.post<ModuleResponse>('/modules', data)
    return response.data
  },

  update: async (id: string, data: UpdateModuleRequest) => {
    const response = await apiClient.put<ModuleResponse>(`/modules/${id}`, data)
    return response.data
  },

  delete: async (id: string) => {
    await apiClient.delete(`/modules/${id}`)
  },

  addSource: async (moduleId: string, sourceId: string) => {
    const response = await apiClient.post(`/modules/${moduleId}/sources/${sourceId}`)
    return response.data
  },

  removeSource: async (moduleId: string, sourceId: string) => {
    const response = await apiClient.delete(`/modules/${moduleId}/sources/${sourceId}`)
    return response.data
  },

  generateOverview: async (moduleId: string, modelId?: string) => {
    const response = await apiClient.post<ModuleResponse>(
      `/modules/${moduleId}/generate-overview`,
      modelId ? { model_id: modelId } : {}
    )
    return response.data
  }
}
