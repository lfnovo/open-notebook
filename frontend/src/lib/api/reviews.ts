import apiClient from './client'

export interface ReviewResponse {
  id: string
  theme: string
  repo_path: string
  notebook_id?: string | null
  status: 'queued' | 'running' | 'completed' | 'failed' | string
  command_id?: string | null
  report_note_id?: string | null
  summary?: Record<string, number> | null
  error_message?: string | null
  created?: string | null
  updated?: string | null
}

export interface CreateReviewRequest {
  theme: string
  repo_path: string
  notebook_id?: string | null
  strategy_model?: string | null
  answer_model?: string | null
  final_answer_model?: string | null
}

export interface ReviewConfigResponse {
  allowed_roots: string[]
}

export const reviewsApi = {
  list: async (params?: { notebook_id?: string }) => {
    const response = await apiClient.get<ReviewResponse[]>('/reviews', { params })
    return response.data
  },

  get: async (id: string) => {
    const response = await apiClient.get<ReviewResponse>(`/reviews/${id}`)
    return response.data
  },

  create: async (data: CreateReviewRequest) => {
    const response = await apiClient.post<ReviewResponse>('/reviews', data)
    return response.data
  },

  delete: async (id: string) => {
    await apiClient.delete(`/reviews/${id}`)
  },

  getConfig: async () => {
    const response = await apiClient.get<ReviewConfigResponse>('/reviews/config')
    return response.data
  },

  getRecentPaths: async () => {
    const response = await apiClient.get<string[]>('/reviews/recent-paths')
    return response.data
  },
}
