import apiClient from './client'

export interface SourceInsightResponse {
  id: string
  source_id: string
  insight_type: string
  content: string
  created: string
  updated: string
}

export interface CreateSourceInsightRequest {
  transformation_id: string
}

export const insightsApi = {
  listForSource: async (sourceId: string) => {
    const response = await apiClient.get<SourceInsightResponse[]>(`/sources/${sourceId}/insights`)
    return response.data
  },

  get: async (insightId: string) => {
    const response = await apiClient.get<SourceInsightResponse>(`/insights/${insightId}`)
    return response.data
  },

  create: async (sourceId: string, data: CreateSourceInsightRequest) => {
    const response = await apiClient.post<SourceInsightResponse>(
      `/sources/${sourceId}/insights`,
      data
    )
    return response.data
  }
}