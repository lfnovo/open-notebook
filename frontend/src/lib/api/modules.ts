import apiClient from './client'
import {
  ModuleResponse,
  CreateModuleRequest,
  UpdateModuleRequest,
  LearningGoalResponse,
  CreateLearningGoalRequest,
  UpdateLearningGoalRequest,
} from '@/lib/types/api'

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
  },

  // Learning Goals API
  getLearningGoals: async (moduleId: string) => {
    const response = await apiClient.get<LearningGoalResponse[]>(
      `/modules/${moduleId}/learning-goals`
    )
    return response.data
  },

  createLearningGoal: async (moduleId: string, data: CreateLearningGoalRequest) => {
    const response = await apiClient.post<LearningGoalResponse>(
      `/modules/${moduleId}/learning-goals`,
      data
    )
    return response.data
  },

  updateLearningGoal: async (goalId: string, data: UpdateLearningGoalRequest) => {
    const response = await apiClient.put<LearningGoalResponse>(
      `/learning-goals/${goalId}`,
      data
    )
    return response.data
  },

  deleteLearningGoal: async (goalId: string) => {
    await apiClient.delete(`/learning-goals/${goalId}`)
  },

  generateLearningGoals: async (moduleId: string, modelId?: string) => {
    const response = await apiClient.post<LearningGoalResponse[]>(
      `/modules/${moduleId}/generate-learning-goals`,
      modelId ? { model_id: modelId } : {}
    )
    return response.data
  },
}
