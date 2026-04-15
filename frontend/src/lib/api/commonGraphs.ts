import apiClient from './client'
import { CommonGraphResponse, CreateCommonGraphRequest } from '@/lib/types/api'

export const commonGraphsApi = {
  create: async (data: CreateCommonGraphRequest) => {
    const response = await apiClient.post<CommonGraphResponse>('/common-graphs', data)
    return response.data
  },

  list: async () => {
    const response = await apiClient.get<CommonGraphResponse[]>('/common-graphs')
    return response.data
  },

  get: async (id: string) => {
    const response = await apiClient.get<CommonGraphResponse>(`/common-graphs/${encodeURIComponent(id)}`)
    return response.data
  },
}
